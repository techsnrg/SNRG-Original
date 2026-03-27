function has_gst_integration() {
    return Boolean(window.india_compliance);
}

function set_gstin_status_description(field, response) {
    const status = response?.message?.status;

    if (!field || !status || !has_gst_integration()) {
        return;
    }

    field.set_description(india_compliance.get_gstin_status_desc(status));
}

function open_mapped_doc(method, frm) {
    frappe.model.open_mapped_doc({
        method,
        frm,
    });
}

frappe.ui.form.on("Lead", {
    custom_gstin(frm) {
        if (!frm.doc.custom_gstin || !has_gst_integration()) {
            return;
        }

        frappe.call({
            method: "india_compliance.gst_india.doctype.gstin.gstin.get_gstin_status",
            args: { gstin: frm.doc.custom_gstin },
            callback: (response) => {
                set_gstin_status_description(frm.get_field("custom_gstin"), response);
            },
        });
    },

    onload_post_render(frm) {
        frm.remove_custom_button(__("Customer"), "Create");
    },

    refresh(frm) {
        if (frm.is_new()) {
            return;
        }

        frm.add_custom_button(__("Secondary Customer"), () => {
            open_mapped_doc("snrg.doc_events.make_secondary_customer", frm);
        }, __("Create"));

        frm.add_custom_button(__("Create Customer"), () => {
            open_mapped_doc("snrg.doc_events.make_customer", frm);
        }, __("Create"));
    },
});
