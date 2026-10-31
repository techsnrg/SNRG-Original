# Isolated valuation repost queue

Target: ERPNext 16.35.0 / Frappe 16.34.0 on the SNRG `develop` deployment.
This change uses per-process routing adapters because ERPNext v16 hardcodes
the long queue for its repost dispatcher and per-item jobs. Recheck these
four ERPNext functions before upgrading: `run_parallel_reposting`,
`enqueue_reposting_entry`, `enqueue_parallel_reposting`, and
`get_entries_with_active_jobs`.

## Deployment order

1. Publish and review the SNRG app change on a branch from `develop`.
2. In bench-46519 Config, merge this into the existing `workers` JSON. Preserve
   any other custom queues:

   ```json
   {
     "valuation_repost": {"timeout": 1800},
     "valuation_repost_2": {"timeout": 1800},
     "valuation_repost_3": {"timeout": 1800},
     "valuation_repost_4": {"timeout": 1800}
   }
   ```

3. Deploy the queue config and the reviewed SNRG app commit together. Keep the
   `snrg_repost_queue` site setting unset during this initial deployment.
   Pin other apps to their existing commits to avoid unrelated upgrades.
4. Verify a healthy RQ Worker subscribed to `valuation_repost` exists and the
   standard short/default and long workers remain available. Check response
   latency and contention before increasing load. Each custom queue creates
   one worker on Frappe Cloud, so the four listed queues create four workers.
5. Add site config `snrg_repost_queue` (String) = `valuation_repost` and apply
   the configuration using Frappe Cloud's normal config deployment/restart.
6. Use ERPNext's supported Execute Repost Item Valuation scheduler action.
   Verify the dispatcher and new per-entry jobs use `valuation_repost`;
   existing long-queue jobs are allowed to drain. Confirm saved progress
   advances and at least one repost completes. No record restart is needed.
7. Confirm the existing day/night Server Script caps dispatch at one item
   10:30–19:00 Asia/Kolkata and four otherwise. It updates approximately every
   five minutes and does not preempt already queued/running jobs or reserve CPU.

The adapter preserves upstream transaction handling, checkpoint recovery,
item exclusion and duplicate skipping. Active IDs are checked in both old
and new queues during transition. An active legacy serial batch blocks the
new dispatcher until a later scheduled run.

## Rollback

Remove `snrg_repost_queue` and apply the config with a worker restart. The
hook restores upstream routing on subsequent requests/jobs. Leave the custom
worker deployed until its queue has drained; pending custom jobs still need
their worker. Only then remove the custom queue and redeploy if desired.
Never delete checkpoint files or manually set reposts Completed.

## Validation

`python3 -m unittest discover -s snrg/tests -p test_repost_queue.py -v`

Sixteen tests cover per-site opt-in/restore, missing queue configuration,
dispatcher isolation, original ledger executor and continuation arguments,
stable deduplication IDs, old/new queue visibility, legacy batch exclusion,
least-busy queue selection, dispatcher locking, dequeue visibility gaps, soon-free worker selection and two-worker/daytime fallback.
These are local contract tests; live deployment verification remains required.

## Capacity limits

This queue isolates worker availability, not CPU, RAM or database I/O. It can
let ordinary long jobs run alongside reposts, but may increase server load.
Verify available hosting capacity and charges before rollout. A single
custom worker still executes one job at a time. New jobs use only the first
one, two or four configured queues according to the Stock Reposting Settings
limit; active jobs on other queues remain counted until finished. Continuations
prefer the worker about to become free. A site-scoped Redis lock serializes
dispatch decisions across workers.

## Four-worker trial and fallback

The user authorized starting with four during the holiday window and reducing
to two if overload appears. Capacity remains unverified on shared hosting.
Watch completion rate, authenticated response latency, persistent database lock
waits, and unexpected worker errors. Do not interpret lifetime worker utilization
as CPU utilization. Normal workers must remain available.

For a persistent fallback, lower the higher limit in the site's `SNRG Reposting
- Day Night Capacity` Server Script from four to two and set
`no_of_parallel_reposting` to two immediately. Changing only the setting is
temporary because the five-minute policy would overwrite it. Leave all queues
configured so active jobs can finish. Monday 2 November 2026 at 10:00 IST the
holiday exception restores one-item dispatch. Jobs already running are not killed.
