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
    # A continuation should run on the worker that is about to become free,
    # rather than wait behind a large repost on the first queue.
    queue_name = select_queue()
    current_job = get_current_job()
    if current_job:
        for name in configured_queues():
            if current_job.origin.endswith(":" + name):
                queue_name = name
                break
    return frappe.enqueue(
        "snrg.repost_queue.run_dispatch",
        queue=queue_name,
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
    try:
        return _ORIGINAL["run_parallel_reposting"]()
    finally:
        lock.release()


def enqueue_entry(name):
    return frappe.enqueue(
        core.execute_reposting_entry,
        name=name,
        continue_reposting=True,
        queue=select_queue(),
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
    def load(name):
        queue = get_queue(name)
        return len(queue.get_job_ids()) + len(queue.started_job_registry.get_job_ids())
    return min(queues, key=load)
