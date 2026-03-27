frappe.provide('frappe.ui.form');

function has_gst_integration() {
    return Boolean(window.india_compliance && window.gst_settings);
}

class GSTQuickEntryForm extends frappe.ui.form.QuickEntryForm {
    constructor(...args) {
        super(...args);
        this.skip_redirect_on_error = true;
        this.api_enabled =
            has_gst_integration() &&
            india_compliance.is_api_enabled() &&
            gst_settings.autofill_party_info;
    }

    async setup() {
        await frappe.model.with_doctype("Address");
        return super.setup();
    }

    render_dialog() {
        super.render_dialog();
        if (has_gst_integration()) {
            india_compliance.set_state_options(this.dialog);
        }
    }

    get_address_fields() {
        return [
            {
                label: __("Primary Address Details"),
                fieldname: "primary_address_section",
                fieldtype: "Section Break",
                description: this.api_enabled
                    ? __(
                          `When you enter a GSTIN, the permanent address linked to it is
                        autofilled.<br>
                        Change the {0} to autofill other addresses.`,
                          [frappe.meta.get_label("Address", "pincode")]
                      )
                    : "",
                collapsible: 0,
            },
            {
                // set as _pincode so that frappe.ui.form.Layout doesn't override it
                fieldname: "_pincode",
                fieldtype: "Autocomplete",
                ignore_validation: true,
            },
            {
                fieldname: "address_line1",
                fieldtype: "Data",
            },
            {
                fieldname: "address_line2",
                fieldtype: "Data",
            },
            {
                fieldtype: "Column Break",
            },
            {
                fieldname: "city",
                fieldtype: "Data",
            },
            {
                fieldname: "state",
                fieldtype: "Autocomplete",
                ignore_validation: true,
            },
            {
                fieldname: "country",
                fieldtype: "Link",
                options: "Country",
                default: frappe.defaults.get_user_default("country"),
                onchange: () => {
                    if (has_gst_integration()) {
                        india_compliance.set_state_options(this.dialog);
                    }
                },
            },
        ];
    }

    get_gstin_field() {
        return [
            {
                ...frappe.meta.get_docfield(this.doctype, "gstin"),
                fieldname: "_gstin",
                fieldtype: "Autocomplete",
                description: this.api_enabled ? get_gstin_description() : "",
                ignore_validation: true,
                onchange: () => {
                    const d = this.dialog;
                    if (this.api_enabled && !gst_settings.sandbox_mode) {
                        return autofill_fields(d);
                    }

                    if (has_gst_integration()) {
                        d.set_value(
                            "gst_category",
                            india_compliance.guess_gst_category(d.doc._gstin, d.doc.country)
                        );
                    }
                },
            },
        ];
    }

    update_doc() {
        const doc = super.update_doc();
        doc.pincode = doc._pincode;
        doc.gstin = doc._gstin;
        doc.address_line1 = doc.address_line1;
        return doc;
    }
}

class SecondaryCustomerQuickEntryForm extends GSTQuickEntryForm {
    get_address_fields() {
        const fields = super.get_address_fields();

        for (const field of fields) {
            const fieldname =
                field.fieldname === "_pincode" ? "pincode" : field.fieldname;

            if (!field.label && fieldname) {
                field.label = frappe.meta.get_label("Address", fieldname);
            }
        }

        return fields;
    }

    get_mandatory_fields(){
        var fields = [{
            label: __("First Name"),
            fieldname: "first_name",
            fieldtype: "Data",
            reqd: 1,
        },
        {
            label: __("Organisation Name"),
            fieldname: "company_name",
            fieldtype: "Data",
            reqd: 1,
        },
        {
            label: __("GST Category"),
            fieldname: "gst_category",
            fieldtype: "Autocomplete",
        },
        {
            label: __("Source"),
            fieldname: "source",
            fieldtype: "Link",
            options: "Lead Source",
        }
    ]
    return fields;
    }

    render_dialog() {
        this.mandatory = [
            ...this.get_gstin_field(),
            ...this.get_mandatory_fields(),
            ...this.get_contact_fields(),
            ...this.get_address_fields(),
        ];

        super.render_dialog();
    }

    get_contact_fields() {
        return [
            {
                label: __("Primary Contact Details"),
                fieldname: "primary_contact_section",
                fieldtype: "Section Break",
                collapsible: 0,
            },
            {
                label: __("Email ID"),
                fieldname: "_email_id",
                fieldtype: "Data",
                options: "Email",
            },
            {
                fieldtype: "Column Break",
            },
            {
                label: __("Mobile Number"),
                fieldname: "_mobile_no",
                fieldtype: "Data",
            },
        ];
    }

    update_doc() {
        const doc = super.update_doc();
        // to prevent clash with ERPNext
        doc._address_line1 = doc.address_line1;
        // these fields were suffixed with _ to prevent them from being read only
        doc.email_id = doc._email_id;
        doc.mobile_no = doc._mobile_no;

        return doc;
    }
}


frappe.ui.form.SecondaryCustomerQuickEntryForm = SecondaryCustomerQuickEntryForm


async function autofill_fields(dialog) {
    const gstin = dialog.doc._gstin;
    const gstin_field = dialog.get_field("_gstin");

    if (!gstin || gstin.length !== 15) {
        const pincode_field = dialog.fields_dict._pincode;
        pincode_field.set_data([]);
        pincode_field.df.onchange = null;

        gstin_field.set_description(get_gstin_description());
        return;
    }

    const gstin_info = await get_gstin_info(gstin);
    set_gstin_description(gstin_field, gstin_info.status);
    map_gstin_info(dialog.doc, gstin_info);
    dialog.set_value('company_name', gstin_info.business_name)
    dialog.set_value('gst_category', gstin_info.gst_category)
    dialog.refresh();

    setup_pincode_field(dialog, gstin_info);
}

function set_gstin_description(gstin_field, status) {
    if (!status) {
        gstin_field.set_description("");
        return;
    }

    if (has_gst_integration()) {
        gstin_field.set_description(india_compliance.get_gstin_status_desc(status));
    }
}

function setup_pincode_field(dialog, gstin_info) {
    if (!gstin_info.all_addresses) return;

    const pincode_field = dialog.fields_dict._pincode;
    pincode_field.set_data(
        gstin_info.all_addresses.map(address => {
            return {
                label: address.pincode,
                value: address.pincode,
                description: `${address.address_line1}, ${address.address_line2}, ${address.city}, ${address.state}`,
            };
        })
    );
    pincode_field.df.onchange = () => {
        autofill_address(dialog.doc, gstin_info);
        dialog.refresh();
    };
}

function get_gstin_info(gstin, throw_error = true) {
    return frappe
        .call({
            method: "india_compliance.gst_india.utils.gstin_info.get_gstin_info",
            args: { gstin, throw_error }
        })
        .then(r => r.message);
}

function map_gstin_info(doc, gstin_info) {
    if (!gstin_info) return;

    update_secondary_customer_info(doc, gstin_info);

    if (gstin_info.permanent_address) {
        update_address_info(doc, gstin_info.permanent_address);
    }
}

function update_secondary_customer_info(doc, gstin_info) {
    doc.gstin = doc._gstin;
    doc.gst_category = gstin_info.gst_category;

    if (!in_list(frappe.boot.gst_party_types, doc.doctype)) return;

    const secondary_customer_name_field = `${doc.doctype.toLowerCase()}_name`;
    doc[secondary_customer_name_field] = gstin_info.business_name;
}

function update_address_info(doc, address) {
    if (!address) return;

    Object.assign(doc, address);
    // set field renamed due conflict with frappe.ui.form.Layout
    doc._pincode = address.pincode;
}

function autofill_address(doc, { all_addresses }) {
    const { _pincode: pincode } = doc;
    if (!pincode || pincode.length !== 6 || !all_addresses) return;

    update_address_info(
        doc,
        all_addresses.find(address => address.pincode == pincode)
    );
}

function get_gstin_description() {
    if (has_gst_integration() && !gst_settings.sandbox_mode) {
        return __("Autofill secondary_customer information by entering their GSTIN");
    }

    return __("Autofill is not supported in sandbox mode");
}
