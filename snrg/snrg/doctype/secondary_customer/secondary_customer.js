// Copyright (c) 2024, administrator and contributors
// For license information, please see license.txt

function has_gst_integration() {
    return Boolean(window.india_compliance);
}

frappe.ui.form.on("Secondary Customer", {
    gstin(frm) {
        if (!frm.doc.gstin || !has_gst_integration()) {
            return;
        }

        frappe.call({
            method: "india_compliance.gst_india.doctype.gstin.gstin.get_gstin_status",
            args: { gstin: frm.doc.gstin },
            callback: (response) => {
                const status = response?.message?.status;
                if (status) {
                    frm.get_field("gstin").set_description(
                        india_compliance.get_gstin_status_desc(status)
                    );
                }
            }
        });
    },
    onload_post_render(frm) {
        
        if (!frm.doc.address_display && !frm.is_new()) {
            frappe.call({
                method: "snrg.doc_events.get_address",
                args: {
                    docname: frm.doc.name
                },
                callback(response) {
                    if (response.message) {
                        frm.set_value("address_display", response.message);
                    }
                }
            });
        }

        if (!frm.doc.contact_display && !frm.is_new()) {
            frappe.call({
                method: "snrg.doc_events.get_contact",
                args: {
                    docname: frm.doc.name
                },
                callback(response) {
                    if (response.message) {
                        frm.set_value("contact_display", response.message);
                    }
                },
            });
        }
    },
})
