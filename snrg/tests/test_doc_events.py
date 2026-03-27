from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from snrg import doc_events


class TestDocEvents(FrappeTestCase):
	def test_validate_gstin_uses_custom_field_for_leads(self):
		doc = SimpleNamespace(
			doctype="Lead",
			custom_gstin="29ABCDE1234F2Z5",
			get_doc_before_save=lambda: None,
		)

		with patch("snrg.doc_events.frappe.db.exists", return_value=True) as exists_mock:
			with patch("snrg.doc_events.frappe.throw", side_effect=RuntimeError("duplicate")) as throw_mock:
				with self.assertRaisesRegex(RuntimeError, "duplicate"):
					doc_events.validate_gstin(doc, None)

		exists_mock.assert_called_once_with("Lead", {"custom_gstin": "29ABCDE1234F2Z5"})
		throw_mock.assert_called_once()

	def test_validate_gstin_uses_standard_field_for_customers(self):
		doc = SimpleNamespace(
			doctype="Customer",
			gstin="29ABCDE1234F2Z5",
			get_doc_before_save=lambda: None,
		)

		with patch("snrg.doc_events.frappe.db.exists", return_value=False) as exists_mock:
			doc_events.validate_gstin(doc, None)

		exists_mock.assert_called_once_with("Customer", {"gstin": "29ABCDE1234F2Z5"})
