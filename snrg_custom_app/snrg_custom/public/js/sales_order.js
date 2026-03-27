function sync_dispatch_address(frm) {
    if (frm.doc.company_address && frm.doc.dispatch_address_name !== frm.doc.company_address) {
        frm.set_value("dispatch_address_name", frm.doc.company_address);
    }
}

function set_today_delivery_date(frm) {
    if (frm.is_new() && !frm.doc.delivery_date) {
        frm.set_value("delivery_date", frappe.datetime.get_today());
    }
}

frappe.ui.form.on("Sales Order", {
    setup(frm) {
        frm.set_query("transporter", {
            filters: {
                is_transporter: 1,
            },
        });
    },

    onload(frm) {
        set_today_delivery_date(frm);
    },

    refresh(frm) {
        sync_dispatch_address(frm);
    },

    company_address(frm) {
        sync_dispatch_address(frm);
    },
});
