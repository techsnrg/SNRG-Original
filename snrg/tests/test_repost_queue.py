"""Routing contract tests, runnable without a live ERPNext database."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class RepostQueueTests(unittest.TestCase):
    def setUp(self):
        self.frappe = ModuleType("frappe")
        self.frappe.conf = {"snrg_repost_queue": "valuation_repost", "workers": {"valuation_repost": {"timeout": 1800}}}
        self.frappe.local = SimpleNamespace(site="example.test")
        self.frappe.enqueue = Mock()
        self.frappe.db = SimpleNamespace(get_single_value=Mock(return_value=1))
        self.lock = Mock()
        self.lock.acquire.return_value = True
        self.frappe.cache = SimpleNamespace(lock=Mock(return_value=self.lock))
        self.core = ModuleType("core")
        for name in ("run_parallel_reposting", "enqueue_reposting_entry", "enqueue_parallel_reposting", "get_entries_with_active_jobs", "execute_reposting_entry"):
            setattr(self.core, name, Mock())
        self.core.REPOSTING_JOB_ID_PREFIX = "repost_item_valuation_entry_"
        background = ModuleType("frappe.utils.background_jobs")
        background.get_job = Mock(return_value=None)
        background.get_queue = Mock(return_value=SimpleNamespace(get_job_ids=lambda: [], started_job_registry=SimpleNamespace(get_job_ids=lambda: [])))
        rq = ModuleType("rq")
        rq.get_current_job = Mock(return_value=None)
        package = ModuleType("erpnext.stock.doctype.repost_item_valuation")
        package.repost_item_valuation = self.core
        self.patcher = patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils.background_jobs": background, "erpnext.stock.doctype.repost_item_valuation": package, "rq": rq})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        spec = importlib.util.spec_from_file_location("routing_under_test", Path(__file__).parents[1] / "repost_queue.py")
        self.routing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.routing)
        self.background = background
        self.rq = rq

    def test_opt_in_and_restore_for_another_site(self):
        original = self.core.run_parallel_reposting
        self.routing.configure_routing()
        self.assertIs(self.core.run_parallel_reposting, self.routing.enqueue_dispatch)
        self.frappe.conf = {}
        self.routing.configure_routing()
        self.assertIs(self.core.run_parallel_reposting, original)

    def test_missing_queue_fails_before_dispatch(self):
        self.frappe.conf["workers"] = {}
        with self.assertRaises(RuntimeError):
            self.routing.configure_routing()
        self.frappe.enqueue.assert_not_called()

    def test_entry_retains_id_recovery_and_continuation(self):
        self.routing.enqueue_entry("riv-1")
        args, kwargs = self.frappe.enqueue.call_args
        self.assertIs(args[0], self.core.execute_reposting_entry)
        self.assertEqual(kwargs, dict(name="riv-1", continue_reposting=True, queue="valuation_repost", timeout=1800, job_id="repost_item_valuation_entry_riv-1", deduplicate=True))

    def test_dispatch_is_queued_on_isolated_worker(self):
        self.routing.enqueue_dispatch()
        args, kwargs = self.frappe.enqueue.call_args
        self.assertEqual(args[0], "snrg.repost_queue.run_dispatch")
        self.assertEqual(kwargs["queue"], "valuation_repost")
        self.assertTrue(kwargs["deduplicate"])

    def test_legacy_serial_batch_blocks_dispatch(self):
        self.background.get_job.return_value = SimpleNamespace(get_status=lambda **kwargs: "started")
        self.routing.run_dispatch()
        self.routing._ORIGINAL["run_parallel_reposting"].assert_not_called()

    def test_original_dispatcher_runs_after_legacy_batch_finishes(self):
        self.routing.run_dispatch()
        self.routing._ORIGINAL["run_parallel_reposting"].assert_called_once_with()
        self.lock.release.assert_called_once_with()

    def test_another_dispatcher_holding_lock_prevents_double_dispatch(self):
        self.lock.acquire.return_value = False
        self.routing.run_dispatch()
        self.routing._ORIGINAL["run_parallel_reposting"].assert_not_called()
        self.lock.release.assert_not_called()

    def test_dispatch_lock_is_released_on_error(self):
        self.routing._ORIGINAL["run_parallel_reposting"].side_effect = ValueError("failed")
        with self.assertRaises(ValueError):
            self.routing.run_dispatch()
        self.lock.release.assert_called_once_with()

    def enable_four_queues(self):
        self.frappe.conf["workers"] = {name: {"timeout": 1800} for name in self.routing.QUEUE_POOL}
        self.frappe.db.get_single_value.return_value = 4

    def test_four_worker_routing_selects_least_busy_queue(self):
        self.enable_four_queues()
        def queue(name):
            count = 0 if name == "valuation_repost_3" else 1
            return SimpleNamespace(get_job_ids=lambda: list(range(count)), started_job_registry=SimpleNamespace(get_job_ids=lambda: []))
        self.background.get_queue.side_effect = queue
        self.routing.enqueue_entry("riv-1")
        self.assertEqual(self.frappe.enqueue.call_args.kwargs["queue"], "valuation_repost_3")

    def test_two_worker_fallback_excludes_extra_queues_for_new_jobs(self):
        self.enable_four_queues()
        self.frappe.db.get_single_value.return_value = 2
        self.routing.select_queue()
        self.assertEqual([call.args[0] for call in self.background.get_queue.call_args_list], ["valuation_repost", "valuation_repost_2"])

    def test_continuation_uses_worker_becoming_free(self):
        self.enable_four_queues()
        self.rq.get_current_job.return_value = SimpleNamespace(origin="bench:valuation_repost_4")
        self.routing.enqueue_dispatch()
        self.assertEqual(self.frappe.enqueue.call_args.kwargs["queue"], "valuation_repost_4")

    def test_active_entries_still_include_extra_queues_at_daytime_cap(self):
        self.enable_four_queues()
        self.frappe.db.get_single_value.return_value = 1
        self.routing.active_entries()
        self.assertEqual([call.args[0] for call in self.background.get_queue.call_args_list], ["long", *self.routing.QUEUE_POOL])

    def test_active_jobs_include_both_queues_and_only_current_site(self):
        prefix = "example.test||repost_item_valuation_entry_"
        def queue(name):
            return SimpleNamespace(get_job_ids=lambda: [prefix + name, "other.test||repost_item_valuation_entry_x"], started_job_registry=SimpleNamespace(get_job_ids=lambda: [prefix + "running"]))
        self.background.get_queue.side_effect = queue
        self.assertEqual(self.routing.active_entries(), {"long", "valuation_repost", "running"})


if __name__ == "__main__":
    unittest.main()
