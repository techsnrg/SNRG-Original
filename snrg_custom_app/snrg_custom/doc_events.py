import frappe
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
    return _make_customer(source_name, target_doc)


def _make_customer(source_name, target_doc=None, ignore_permissions=False):
    def set_missing_values(source, target):
        if source.company_name:
            target.customer_type = "Company"
            target.customer_name = source.company_name
        else:
            target.customer_type = "Individual"
            target.customer_name = source.lead_name

        target.customer_group = frappe.db.get_default("Customer Group")

    return get_mapped_doc(
        "Lead",
        source_name,
        {
            "Lead": {
                "doctype": "Customer",
                "field_map": {
                    "name": "lead_name",
                    "company_name": "customer_name",
                    "contact_no": "phone_1",
                    "fax": "fax_1",
                    "custom_gstin": "gstin",
                },
                "field_no_map": ["disabled"],
            }
        },
        target_doc,
        set_missing_values,
        ignore_permissions=ignore_permissions,
    )


def validate_gstin(doc, method=None):
    if doc.get_doc_before_save():
        return

    if doc.doctype == "Lead":
        gstin_field = "custom_gstin"
    else:
        gstin_field = "gstin"

    gstin = getattr(doc, gstin_field, None)
    if not gstin:
        return

    if frappe.db.exists(doc.doctype, {gstin_field: gstin}):
        frappe.throw(
            f"The GSTIN Number that you are entered is already exists in {doc.doctype}"
        )


def create_address(doc, method=None):
    if doc.get_doc_before_save():
        return

    address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": doc.get("name"),
            "address_line1": doc.get("address_line1"),
            "address_line2": doc.get("address_line2"),
            "city": doc.get("city"),
            "state": doc.get("state"),
            "pincode": doc.get("pincode"),
            "country": doc.get("country"),
            "is_primary_address": 1,
            "links": [{"link_doctype": doc.get("doctype"), "link_name": doc.get("name")}],
        }
    )
    address.insert()
