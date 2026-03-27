app_name = "snrg_custom"
app_title = "SNRG Custom"
app_publisher = "administrator"
app_description = "Clean SNRG customizations for ERPNext"
app_email = "hello@aerele.in"
app_license = "mit"

app_include_js = ["public/js/lead_quick_entry.js"]

doctype_js = {
    "Lead": "public/js/lead.js",
    "Sales Order": "public/js/sales_order.js",
}

doc_events = {
    "Lead": {
        "before_save": "snrg_custom.doc_events.validate_gstin",
        "on_update": "snrg_custom.doc_events.create_address",
    },
    "Customer": {
        "before_save": "snrg_custom.doc_events.validate_gstin",
    },
    "Supplier": {
        "before_save": "snrg_custom.doc_events.validate_gstin",
    },
}

override_whitelisted_methods = {}
