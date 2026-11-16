# Early form styling

`snrg_form_layout.bundle.css` is loaded through `app_include_css` in the Desk
document head. Selectors use existing Quotation and Stock Entry page/tab IDs;
they do not depend on refresh events or a JavaScript-added class. The stylesheet
is restricted to these Details tabs and does not style the credit dashboard.

Field order and other site customizations remain site-owned. Business JavaScript,
Python handlers, pricing, stock calculations and credit policy are unchanged.

After deploying and verifying that the hashed stylesheet is in the Desk head:

1. Disable the site Client Script `SNRG Quotation Compact Layout` (CSS only).
2. Retain `SNRG Stock Entry Compact Layout` as an output-summary renderer. Replace
   its inline summary styles with `snrg-se-output-summary`, and remove only the
   quantity/button `.css()` calls. The existing `from_bom` depends_on conditions
   continue to control both fields' visibility.
3. Check direct loads and navigation on desktop: Quotation, Stock Entry Manufacture,
   Repack and Material Transfer, including turning From BOM on and off.

Do not disable the old styling until the new asset is live. To roll back, restore
the backed-up Client Scripts before reverting the stylesheet hook. Rebuild assets
and refresh the Desk page after app updates; do not re-export layout Property
Setters to this app as part of this change.
