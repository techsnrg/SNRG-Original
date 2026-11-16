# Sales form layout ownership

Quotation, Quotation Item, Sales Order and Sales Order Item use site-owned layouts.
Manage their field order, item-grid display and widths, section collapse state and
display labels through **Customize Form** on the site.

The app still owns the custom-field definitions and functional Property Setters in
these exports. Keep `sync_on_migrate` enabled for those settings. In particular,
preserve hidden/read-only/required flags, defaults, options, fetch rules, rounding,
print settings and copy behavior unless separately reviewed. JavaScript and Python
business behavior are independent of this layout cleanup.

## What this change does

It removes 40 presentation-only Property Setters from the four customization JSON
files. It does not delete Custom Fields, remove settings from the live database,
change transactions, or reset existing layouts to ERPNext defaults. Initial
placement anchors in Custom Field definitions remain available for new installs;
the site's final field order remains a site customization.

Removing an export stops that setting being reapplied by this app during future
migrations. Existing installed Property Setters remain on the site. To change the
current layout, edit it separately through Customize Form after reviewing the v16
fields.

When exporting functional customizations back into this app, exclude these
presentation properties for these four DocTypes:

- `field_order`
- `columns`
- `in_list_view`
- `collapsible`
- `label`

Keep the layout properties in the site's own customization backup instead. Lead,
Secondary Customer quick entry and Packed Item are outside this change.

## Rollout and verification

1. Back up the site's Custom Fields, Property Setters and Client Scripts for the
   four DocTypes. Record the deployed app branch/commit and the database backup.
2. Apply this patch to the branch actually deployed on the site. The repository's
   default branch is not proof of the deployed branch.
3. In a staging copy, migrate and verify that the installed layout Property Setters
   remain unchanged. Confirm that all custom-field definitions and retained
   functional settings are still present.
4. Check a quotation, quotation-to-sales-order conversion, sales-order address and
   transporter behavior, and sales-order-to-invoice conversion without submitting
   test transactions in production.
5. Make any desired v16 layout changes through Customize Form. Migrate staging
   again to confirm that the app no longer restores the exported old layout.

No automatic cleanup patch deletes live Property Setters. To roll back before site
layout edits, restore these JSON exports. If layouts have since been edited,
restore the reviewed site backup rather than blindly reapplying old exports.
