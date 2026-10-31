"""Route ERPNext v16 reposts to an opt-in, dedicated Frappe Cloud queue.

ERPNext's dispatcher, transaction reposts, per-item jobs and continuations all
use the dedicated queue. Ledger calculation and checkpoints remain upstream.
Set snrg_repost_queue to valuation_repost only after that worker is deployed.
"""

import frappe
from erpnext.stock.doctype.repost_item_valuation import repost_item_valuation as core
from frappe.utils.background_jobs import get_job, get_queue
from rq import get_current_job


QUEUE = "valuation_repost"
QUEUE_POOL = (QUEUE, "valuation_repost_2", "valuation_repost_3", "valuation_repost_4")
_NAMES = (
    "run_parallel_reposting",
    "enqueue_reposting_entry",
    "enqueue_parallel_reposting",
    "get_entries_with_active_jobs",
)
_ORIGINAL = {name: getattr(core, name) for name in _NAMES}


def configure_routing(**kwargs):
    """Install or restore routing per site/request, including shared processes."""
    enabled = frappe.conf.get("snrg_repost_queue") == QUEUE
    if enabled and QUEUE not in (frappe.conf.get("workers") or {}):
        raise RuntimeError("valuation_repost worker configuration is missing")
    replacements = {
        "run_parallel_reposting": enqueue_dispatch,
        "enqueue_reposting_entry": enqueue_entry,
        "enqueue_parallel_reposting": enqueue_dispatch,
        "get_entries_with_active_jobs": active_entries,
    }
    for name in _NAMES:
        setattr(core, name, replacements[name] if enabled else _ORIGINAL[name])


def enqueue_dispatch():
    return frappe.enqueue(
        "snrg.repost_queue.run_dispatch",
        queue=select_queue(),
        timeout=1800,
        job_id="snrg_valuation_repost_dispatch",
        deduplicate=True,
    )


def run_dispatch():
    # Allow any pre-deployment serial batch to finish before resuming its rows.
    legacy = get_job("scheduled_job||repost_item_valuation.repost_entries")
    if legacy and legacy.get_status(refresh=True) == "started":
        return
    # The original dispatcher keeps settings, timeslot, item exclusion and
    # dependency handling. Its transaction-based work now runs on this worker.
    # More than one worker can finish at once. Serialize dispatcher decisions
    # so they cannot independently fill the same available item slots.
    lock = frappe.cache.lock(f"snrg_repost_dispatch:{frappe.local.site}", timeout=1900)
    if not lock.acquire(blocking=False):
        return
    frappe.local.snrg_repost_reservations = {}
    try:
        return _ORIGINAL["run_parallel_reposting"]()
    finally:
        frappe.local.snrg_repost_reservations = {}
        lock.release()


def enqueue_entry(name):
    queue_name = select_queue()
    reservations = getattr(frappe.local, "snrg_repost_reservations", None)
    if reservations is not None:
        reservations[queue_name] = reservations.get(queue_name, 0) + 1
    return frappe.enqueue(
        core.execute_reposting_entry,
        name=name,
        continue_reposting=True,
        queue=queue_name,
        timeout=1800,
        job_id=f"{core.REPOSTING_JOB_ID_PREFIX}{name}",
        deduplicate=True,
    )


def active_entries():
    """Include old long-queue jobs during the transition, without requeueing them."""
    entries = set()
    prefix = f"{frappe.local.site}||{core.REPOSTING_JOB_ID_PREFIX}"
    # Include every configured pool queue even after the daytime/fallback cap
    # shrinks, so jobs already running on the extra workers remain visible.
    for queue_name in ("long", *configured_queues()):
        queue = get_queue(queue_name)
        job_ids = list(queue.get_job_ids()) + list(queue.started_job_registry.get_job_ids())
        entries.update(job_id[len(prefix):] for job_id in job_ids if job_id.startswith(prefix))
    return entries


def configured_queues():
    workers = frappe.conf.get("workers") or {}
    return tuple(name for name in QUEUE_POOL if name in workers)


def select_queue():
    limit = int(frappe.db.get_single_value("Stock Reposting Settings", "no_of_parallel_reposting") or 1)
    queues = configured_queues()[: max(1, min(limit, len(QUEUE_POOL)))]
    if not queues:
        raise RuntimeError("valuation_repost worker configuration is missing")
    current_job = get_current_job()
    def load(name):
        queue = get_queue(name)
        # A worker can dequeue a job before RQ publishes it in the started
        # registry. Keep this dispatch's assignments visible through that gap.
        reserved = (getattr(frappe.local, "snrg_repost_reservations", None) or {}).get(name, 0)
        count = len(queue.get_job_ids()) + len(queue.started_job_registry.get_job_ids())
        # The caller releases its worker before its enqueued work can run.
        # Counting that caller makes a free-soon worker look as busy as a
        # different worker running a long repost, creating queued work there.
        if current_job and current_job.origin.endswith(":" + name):
            count = max(0, count - 1)
        return count + reserved
    return min(queues, key=load)
