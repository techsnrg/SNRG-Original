frappe.ui.form.on("Quotation", {
    onload(frm) {
        // List filters are copied directly into new documents without firing
        // the party_name event. Fetch the full Customer context so pricing
        // rules use the correct Customer Group and Territory.
        if (
            frm.is_new() &&
            frm.doc.quotation_to === "Customer" &&
            frm.doc.party_name
        ) {
            frm.trigger("party_name");
        }
    },

    refresh(frm) {
        frm.set_query("transporter", {
            filters: {
                is_transporter: 1
            },
        });
    }
    // setup(frm) {
    //     frm.set_query("transporter", {
    //         filters: {
    //             is_transporter: 1,
    //         },
    //     });
    // }
});
