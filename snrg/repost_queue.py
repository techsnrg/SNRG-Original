"""Route ERPNext v16 reposts to an opt-in, dedicated Frappe Cloud queue.

ERPNext's dispatcher, transaction reposts, per-item jobs and continuations all
use the dedicated queue. Ledger calculation and checkpoints remain upstream.
Set snrg_repost_queue to valuation_repost only after that worker is deployed.
"""

import frappe
from erpnext.stock.doctype.repost_item_valuation import repost_item_valuation as core
from frappe.utils.background_jobs import get_job, get_queue


QUEUE = "valuation_repost"
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
        queue=QUEUE,
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
    return _ORIGINAL["run_parallel_reposting"]()


def enqueue_entry(name):
    return frappe.enqueue(
        core.execute_reposting_entry,
        name=name,
        continue_reposting=True,
        queue=QUEUE,
        timeout=1800,
        job_id=f"{core.REPOSTING_JOB_ID_PREFIX}{name}",
        deduplicate=True,
    )


def active_entries():
    """Include old long-queue jobs during the transition, without requeueing them."""
    entries = set()
    prefix = f"{frappe.local.site}||{core.REPOSTING_JOB_ID_PREFIX}"
    for queue_name in ("long", QUEUE):
        queue = get_queue(queue_name)
        job_ids = list(queue.get_job_ids()) + list(queue.started_job_registry.get_job_ids())
        entries.update(job_id[len(prefix):] for job_id in job_ids if job_id.startswith(prefix))
    return entries
