from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from snrg_custom import doc_events


class TestDocEvents(FrappeTestCase):
    def test_validate_gstin_uses_custom_field_for_leads(self):
        doc = SimpleNamespace(
            doctype="Lead",
            custom_gstin="29ABCDE1234F2Z5",
            get_doc_before_save=lambda: None,
        )

        with patch("snrg_custom.doc_events.frappe.db.exists", return_value=True) as exists_mock:
            with patch(
                "snrg_custom.doc_events.frappe.throw", side_effect=RuntimeError("duplicate")
            ) as throw_mock:
                with self.assertRaisesRegex(RuntimeError, "duplicate"):
                    doc_events.validate_gstin(doc)

        exists_mock.assert_called_once_with("Lead", {"custom_gstin": "29ABCDE1234F2Z5"})
        throw_mock.assert_called_once()

    def test_validate_gstin_uses_standard_field_for_customers(self):
        doc = SimpleNamespace(
            doctype="Customer",
            gstin="29ABCDE1234F2Z5",
            get_doc_before_save=lambda: None,
        )

        with patch("snrg_custom.doc_events.frappe.db.exists", return_value=False) as exists_mock:
            doc_events.validate_gstin(doc)

        exists_mock.assert_called_once_with("Customer", {"gstin": "29ABCDE1234F2Z5"})

    def test_create_address_inserts_address_for_new_lead(self):
        inserted = {}

        class FakeAddress:
            def insert(self_inner):
                inserted["called"] = True

        doc = SimpleNamespace(
            get_doc_before_save=lambda: None,
            get=lambda key: {
                "name": "LEAD-0001",
                "doctype": "Lead",
                "address_line1": "Line 1",
                "address_line2": "Line 2",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "country": "India",
            }.get(key),
        )

        with patch("snrg_custom.doc_events.frappe.get_doc", return_value=FakeAddress()) as get_doc_mock:
            doc_events.create_address(doc)

        get_doc_mock.assert_called_once()
        self.assertTrue(inserted["called"])

    def test_make_customer_maps_custom_gstin(self):
        captured = {}

        def fake_get_mapped_doc(source_dt, source_name, table_maps, target_doc, postprocess, **kwargs):
            captured["source_dt"] = source_dt
            captured["source_name"] = source_name
            captured["field_map"] = table_maps["Lead"]["field_map"]
            captured["ignore_permissions"] = kwargs.get("ignore_permissions")

            source = SimpleNamespace(company_name="Acme", lead_name="Lead Person")
            target = SimpleNamespace(customer_type=None, customer_name=None, customer_group=None)
            postprocess(source, target)
            captured["target"] = target
            return target

        with patch("snrg_custom.doc_events.get_mapped_doc", side_effect=fake_get_mapped_doc):
            with patch("snrg_custom.doc_events.frappe.db.get_default", return_value="All Customer Groups"):
                result = doc_events.make_customer("LEAD-0001")

        self.assertEqual(captured["source_dt"], "Lead")
        self.assertEqual(captured["source_name"], "LEAD-0001")
        self.assertEqual(captured["field_map"]["custom_gstin"], "gstin")
        self.assertEqual(result.customer_type, "Company")
        self.assertEqual(result.customer_name, "Acme")
        self.assertEqual(result.customer_group, "All Customer Groups")
