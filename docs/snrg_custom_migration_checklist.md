# SNRG Custom Migration Checklist

This checklist captures the approved scope for the new `snrg_custom` app.

## Keep

### Core

- Keep `india_compliance` integration where required for GST fetch and status behavior.
- Keep targeted client scripts only where they support retained features.
- Avoid a broad global JS bundle unless a later feature truly needs one.

### Lead

- Keep `custom_gstin`.
- Keep `custom_lead_owner_name`.
- Keep Lead quick entry customizations.
- Keep GSTIN autofill from `india_compliance`.
- Keep GST status display.
- Keep mobile uniqueness.
- Keep India/default request type behavior.
- Keep Lead list/search/filter improvements where still useful.
- Keep Lead create actions for Customer conversion.
- Keep automatic Address creation on new Lead updates.
- Keep GST duplicate validation.

### Customer and Supplier

- Keep Lead to Customer mapping.
- Keep mapping Lead `custom_gstin` to Customer `gstin`.
- Keep GST duplicate validation for Customer and Supplier.

### Quotation

- Keep `po_no`.
- Keep `po_date`.
- Keep GST-related custom fields:
  - `is_reverse_charge`
  - `gst_breakup_table`
  - `section_gst_breakup`
  - `company_gstin`
  - `place_of_supply`
  - `gst_category`
  - `billing_address_gstin`
  - `is_export_with_gst`
- Keep `custom_incoterms`.
- Keep `custom_additionals`.
- Keep Quotation Item grid visibility and GST row details.

### Sales Order

- Keep `transporter`.
- Keep `custom_mobile_number`.
- Keep GST-related custom fields:
  - `is_reverse_charge`
  - `gst_breakup_table`
  - `section_gst_breakup`
  - `company_gstin`
  - `place_of_supply`
  - `gst_category`
  - `billing_address_gstin`
  - `ecommerce_gstin`
  - `gst_section`
  - `is_export_with_gst`
- Keep `custom_incoterms`.
- Keep `custom_additionals`.
- Keep `custom_additional_fields`.
- Keep `delivery_date` required.
- Set `delivery_date` to today for new Sales Orders.
- Keep `set_warehouse` fetch behavior.
- Keep transporter filtering.
- Keep dispatch address sync from company address.
- Keep Sales Order Item grid visibility and GST row details.

## Rewrite Minimally

- Rebuild only the exact custom fields and property setters required for retained features.
- Rebuild Lead quick entry and GST helper logic without carrying unrelated legacy code.
- Rebuild Customer conversion logic as smaller, testable helpers.
- Rebuild any mapping override only if standard ERPNext flow proves insufficient after testing.

## Drop

- Drop `custom_customer_category`.
- Drop competitors-related Lead features and DocTypes.
- Drop `Secondary Customer` entirely.
- Drop Quotation `transporter`.
- Drop Quotation `custom_station`.
- Drop Quotation naming series override.
- Drop Quotation layout-only reordering and hidden-field legacy clutter.
- Drop Sales Order `custom_pm`.
- Drop Sales Order `custom_station`.
- Drop Sales Order layout-only reordering and old default print format behavior.
- Drop Sales Order cost center fetch from Customer.
- Drop editable `Packed Item.rate`.
- Drop `Calls`.
- Drop `Call Outcome`.
- Drop `Counter`.
- Drop `Field Visits`.
- Drop legacy print formats.

## Overrides

- Start without Quotation to Sales Order override.
- Start without Sales Order to Sales Invoice override.
- Add a very small override later only if testing reveals a specific missing mapping or behavior.

## Build Order

1. Minimal custom fields and property setters for Lead, Quotation, Sales Order, and item grids.
2. Sales Order client behavior.
3. Lead GST validation and quick entry behavior.
4. Lead to Customer mapping.
5. Re-test standard ERPNext document mappings before deciding on overrides.
