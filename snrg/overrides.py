import json

import frappe
from frappe import _, whitelist
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, flt, getdate, nowdate


def _coerce_customer(customer):
	if not customer:
		return None

	if isinstance(customer, str):
		if frappe.db.exists("Customer", customer):
			return frappe.get_doc("Customer", customer)
		return None

	if getattr(customer, "doctype", None) == "Customer":
		return customer

	return None


def _resolve_customer(source_name, ignore_permissions=False):
	customer = None

	try:
		from erpnext.selling.doctype.quotation.quotation import _make_customer

		customer = _make_customer(source_name, ignore_permissions)
	except Exception:
		customer = None

	customer = _coerce_customer(customer)
	if customer:
		return customer

	quotation = frappe.db.get_value(
		"Quotation",
		source_name,
		["quotation_to", "party_name", "lead"],
		as_dict=1,
	) or frappe._dict()

	customer_candidates = []
	if quotation.quotation_to == "Customer" and quotation.party_name:
		customer_candidates.append(quotation.party_name)

	if quotation.lead:
		lead_customer = frappe.db.get_value("Lead", quotation.lead, "customer")
		if lead_customer:
			customer_candidates.append(lead_customer)

		customer_from_lead = frappe.db.get_value("Customer", {"lead_name": quotation.lead}, "name")
		if customer_from_lead:
			customer_candidates.append(customer_from_lead)

	for customer_name in customer_candidates:
		if frappe.db.exists("Customer", customer_name):
			return frappe.get_doc("Customer", customer_name)

	return None


@frappe.whitelist()
def make_sales_order(source_name: str, target_doc=None, args=None):
	if not frappe.db.get_singles_value(
		"Selling Settings", "allow_sales_order_creation_for_expired_quotation"
	):
		quotation = frappe.db.get_value(
			"Quotation", source_name, ["transaction_date", "valid_till"], as_dict=1
		)
		if quotation.valid_till and (
			quotation.valid_till < quotation.transaction_date or quotation.valid_till < getdate(nowdate())
		):
			frappe.throw(_("Validity period of this quotation has ended."))

	return _make_sales_order(source_name, target_doc, args=args)


def _make_sales_order(source_name, target_doc=None, ignore_permissions=False, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	customer = _resolve_customer(source_name, ignore_permissions)
	ordered_items = frappe._dict(
		frappe.get_all(
			"Quotation Item",
			{"docstatus": 1, "parent": source_name, "ordered_qty": (">", 0)},
			["name", "ordered_qty"],
			as_list=True,
		)
	)

	selected_rows = [x.get("name") for x in frappe.flags.get("args", {}).get("selected_items", [])]
	has_unit_price_items = frappe.db.get_value("Quotation", source_name, "has_unit_price_items")

	def is_unit_price_row(source) -> bool:
		return has_unit_price_items and source.qty == 0

	def set_missing_values(source, target):
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

			# sales team
			if not target.get("sales_team"):
				for d in customer.get("sales_team") or []:
					target.append(
						"sales_team",
						{
							"sales_person": d.sales_person,
							"allocated_percentage": d.allocated_percentage or None,
							"commission_rate": d.commission_rate,
						},
					)

		if source.referral_sales_partner:
			target.sales_partner = source.referral_sales_partner
			target.commission_rate = frappe.get_value(
				"Sales Partner", source.referral_sales_partner, "commission_rate"
			)

		target.flags.ignore_permissions = ignore_permissions
		target.delivery_date = nowdate()

		# Preserve the pricing agreed on the submitted Quotation. Sales Order's
		# set_missing_values recalculates pricing rules for every mapped row and
		# can replace the copied rules and rates with a currently matching rule.
		mapped_pricing_rules = list(target.get("pricing_rules") or [])
		ignore_pricing_rule = target.get("ignore_pricing_rule")
		try:
			target.ignore_pricing_rule = 1
			target.run_method("set_missing_values")
		finally:
			target.ignore_pricing_rule = ignore_pricing_rule
			target.set("pricing_rules", mapped_pricing_rules)

		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		balance_stock_qty = obj.stock_qty - ordered_items.get(obj.name, 0.0)
		target.stock_qty = balance_stock_qty if balance_stock_qty > 0 else 0
		target.qty = flt(target.stock_qty) / flt(obj.conversion_factor)

		if obj.against_blanket_order:
			target.against_blanket_order = obj.against_blanket_order
			target.blanket_order = obj.blanket_order
			target.blanket_order_rate = obj.blanket_order_rate

	def can_map_row(item) -> bool:
		"""
		Row mapping from Quotation to Sales order:
		1. If no selections, map all non-alternative rows (that sum up to the grand total)
		2. If selections: Is Alternative Item/Has Alternative Item: Map if selected and adequate qty
		3. If no selections: Simple row: Map if adequate qty
		"""
		if not ((item.stock_qty > ordered_items.get(item.name, 0.0)) or is_unit_price_row(item)):
			return False

		if not selected_rows:
			return not item.is_alternative

		if selected_rows and (item.is_alternative or item.has_alternative_item):
			return item.name in selected_rows

		# Simple row
		return True

	def select_item(item):
		filtered_items = args.get("filtered_children", [])
		return item.name in filtered_items if filtered_items else True

	automatically_fetch_payment_terms = cint(
		frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)

	doclist = get_mapped_doc(
		"Quotation",
		source_name,
		{
			"Quotation": {
				"doctype": "Sales Order",
				"field_map": {"po_no": "po_no", "transporter": "transporter"},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Quotation Item": {
				"doctype": "Sales Order Item",
				"field_map": {"parent": "prevdoc_docname", "name": "quotation_item"},
				"postprocess": update_item,
				"condition": lambda item: can_map_row(item) and select_item(item),
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "reset_value": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	return doclist


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
	def postprocess(source, target):
		set_missing_values(source, target)
		# Get the advance paid Journal Entries in Sales Invoice Advance
		if target.get("allocate_advances_automatically"):
			target.set_advances()

	def set_missing_values(source, target):
		from frappe.contacts.doctype.address.address import get_company_address
		from frappe.model.utils import get_fetch_values
		from erpnext.accounts.party import get_party_account

		target.flags.ignore_permissions = True
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_use_serial_batch_fields")

		if source.company_address:
			target.update({"company_address": source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Sales Invoice", "company_address", target.company_address))

		# set the redeem loyalty points if provided via shopping cart
		if source.loyalty_points and source.order_type == "Shopping Cart":
			target.redeem_loyalty_points = 1

		target.debit_to = get_party_account("Customer", source.customer, source.company)

	def update_item(source, target, source_parent):
		from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
		from erpnext.stock.doctype.item.item import get_item_defaults

		target.amount = flt(source.amount) - flt(source.billed_amt)
		target.base_amount = target.amount * flt(source_parent.conversion_rate)
		target.qty = (
			target.amount / flt(source.rate)
			if (source.rate and source.billed_amt)
			else source.qty - source.returned_qty
		)

		if source_parent.project:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center")
		if target.item_code:
			item = get_item_defaults(target.item_code, source_parent.company)
			item_group = get_item_group_defaults(target.item_code, source_parent.company)
			cost_center = item.get("selling_cost_center") or item_group.get("selling_cost_center")

			if cost_center:
				target.cost_center = cost_center

	doclist = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Sales Invoice",
				"field_map": {
					"party_account_currency": "party_account_currency",
					"payment_terms_template": "payment_terms_template",
					"transporter": "transporter",
				},
				"field_no_map": ["payment_terms_template"],
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Sales Invoice Item",
				"field_map": {
					"name": "so_detail",
					"parent": "sales_order",
				},
				"postprocess": update_item,
				"condition": lambda doc: doc.qty
				and (doc.base_amount == 0 or abs(doc.billed_amt) < abs(doc.amount)),
			},
			"Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
			"Sales Team": {"doctype": "Sales Team", "add_if_empty": True},
		},
		target_doc,
		postprocess,
		ignore_permissions=ignore_permissions,
	)

	automatically_fetch_payment_terms = cint(
		frappe.db.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
	)
	if automatically_fetch_payment_terms:
		doclist.set_payment_schedule()

	return doclist
