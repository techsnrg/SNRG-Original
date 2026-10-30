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
        self.core = ModuleType("core")
        for name in ("run_parallel_reposting", "enqueue_reposting_entry", "enqueue_parallel_reposting", "get_entries_with_active_jobs", "execute_reposting_entry"):
            setattr(self.core, name, Mock())
        self.core.REPOSTING_JOB_ID_PREFIX = "repost_item_valuation_entry_"
        background = ModuleType("frappe.utils.background_jobs")
        background.get_job = Mock(return_value=None)
        background.get_queue = Mock()
        package = ModuleType("erpnext.stock.doctype.repost_item_valuation")
        package.repost_item_valuation = self.core
        self.patcher = patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils.background_jobs": background, "erpnext.stock.doctype.repost_item_valuation": package})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        spec = importlib.util.spec_from_file_location("routing_under_test", Path(__file__).parents[1] / "repost_queue.py")
        self.routing = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.routing)
        self.background = background

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

    def test_active_jobs_include_both_queues_and_only_current_site(self):
        prefix = "example.test||repost_item_valuation_entry_"
        def queue(name):
            return SimpleNamespace(get_job_ids=lambda: [prefix + name, "other.test||repost_item_valuation_entry_x"], started_job_registry=SimpleNamespace(get_job_ids=lambda: [prefix + "running"]))
        self.background.get_queue.side_effect = queue
        self.assertEqual(self.routing.active_entries(), {"long", "valuation_repost", "running"})


if __name__ == "__main__":
    unittest.main()
