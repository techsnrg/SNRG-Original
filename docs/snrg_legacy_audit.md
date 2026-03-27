# SNRG Legacy App Audit

This audit groups the current `snrg` app into `keep`, `rewrite`, and `drop` so we can rebuild only the useful ERPNext behavior in a new app.

## Recommendation

Build a new app and treat the current `snrg` app as reference code only.

Reason:
- The app mixes unrelated concerns in one package.
- A large amount of behavior lives in exported JSON customizations, which is hard to maintain safely.
- Some logic is stale, incomplete, or brittle.
- The current app already contains at least one hook bug caused by duplicate keys in `doc_events`.

## Keep

These are the parts most worth carrying into the new app.

### Selling flow

- Quotation custom fields that support sales operations:
  - `transporter`
  - `po_no`
  - `po_date`
  - `custom_station`
  - `custom_incoterms`
  - `custom_additionals`
- Sales Order custom fields that support order execution:
  - `transporter`
  - `custom_pm`
  - `custom_mobile_number`
  - `custom_station`
  - `custom_incoterms`
  - `custom_additionals`
- Grid visibility fixes for `Quotation Item.item_name` and `Sales Order Item.item_name`.
- Transporter link filtering in Quotation and Sales Order client scripts.
- Custom Quotation to Sales Order mapping for:
  - quotation validity check
  - `po_no`
  - `transporter`
  - delivery date
  - referral sales partner and commission
- Custom Sales Order to Sales Invoice mapping for:
  - `transporter`
  - company address handling
  - billed balance logic
  - cost center selection

### GST and India compliance integration

- GSTIN uniqueness validation logic.
- Lead quick entry GST autofill.
- Secondary Customer quick entry GST autofill.
- GSTIN status display on Lead and Secondary Customer forms.

### Print

- Rebuild only the Sales Invoice print formats if those layouts are still actively used.

## Rewrite

These features may still be useful, but they should be rebuilt cleanly rather than copied as-is.

### Lead and customer conversion

- Lead to Customer mapping.
- Lead to Secondary Customer mapping.
- Automatic address and contact creation.

Why rewrite:
- The logic is tightly coupled to current field choices.
- It would be better as cleaner, smaller functions with explicit tests.

### Secondary Customer concept

- Keep only if the business still truly uses a second CRM entity distinct from Customer and Lead.

Why rewrite:
- The DocType is broad and CRM-heavy.
- It likely includes more fields than the business actually needs.

### Exported form layouts

- Lead, Quotation, Sales Order, Quotation Item, and Sales Order Item custom JSON.

Why rewrite:
- The current exports include many hidden/defaulted/property-setter changes that are hard to justify one by one.
- Rebuilding from a minimal feature checklist will be safer than carrying old layout debt.

### Print formats

- Recreate only one canonical invoice format if needed.

Why rewrite:
- There are two similar tax invoice formats.
- Print format HTML is long and hard to maintain.

## Drop

These are the strongest candidates to leave behind entirely unless the business confirms they still matter.

- `Counter` DocType.
- `Field Visits` DocType.
- `Calls` DocType.
- `Call Outcome` DocType.
- Bulk counter sync logic.
- Incomplete `Field Visits` query helpers.
- Legacy layout changes that only hide core ERPNext fields without adding clear business value.

Reason:
- These features are separate mini-products.
- They add maintenance overhead.
- Some appear unfinished or loosely integrated.

## Known issues in the legacy app

### Duplicate hook keys

In `snrg/hooks.py`, multiple DocTypes define `before_save` twice inside the same dictionary. In Python, the latter key wins, so the earlier entry is lost.

Effect:
- `validate_gstin` runs.
- `insert_or_update_document` for the `Counter` DocType likely does not run from hooks.

### Large JSON customization surface

The app relies heavily on exported customizations. This makes it difficult to:
- review intent
- test behavior
- remove unused changes safely

### Mixed responsibilities

The app combines:
- CRM customization
- GST integration
- selling document overrides
- logistics fields
- custom print formats
- custom mini-CRM doctypes

This should be split into smaller, clearer modules in the replacement app.

## Rebuild order

Recommended migration sequence:

1. Base app scaffold and hooks.
2. Quotation and Sales Order field additions.
3. Item grid visibility and selling form client scripts.
4. Quotation to Sales Order override.
5. Sales Order to Sales Invoice override.
6. GST validation helpers.
7. Lead quick entry GST autofill.
8. Secondary Customer decision:
   - either rebuild minimally
   - or remove the concept entirely
9. Print format rebuild.

## Decision summary

Default path:
- Keep selling and GST pieces.
- Rewrite conversion and form logic.
- Drop custom activity-tracking doctypes unless explicitly required.
