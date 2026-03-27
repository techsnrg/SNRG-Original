app_name = "snrg"
app_title = "SNRG"
app_publisher = "administrator"
app_description = "SNRG"
app_email = "hello@aerele.in"
app_license = "mit"
required_apps = ["erpnext", "india_compliance"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/snrg/css/snrg.css"
# app_include_js = "/assets/snrg/js/snrg.js"

app_include_js = "snrg.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/snrg/css/snrg.css"
# web_include_js = "/assets/snrg/js/snrg.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "snrg/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
            "Lead" : "public/js/lead.js",
            "Quotation" : "public/js/quotation.js",
            "Sales Order" : "public/js/sales_order.js"
        }
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "snrg/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "snrg.utils.jinja_methods",
# 	"filters": "snrg.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "snrg.install.before_install"
# after_install = "snrg.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "snrg.uninstall.before_uninstall"
# after_uninstall = "snrg.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "snrg.utils.before_app_install"
# after_app_install = "snrg.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "snrg.utils.before_app_uninstall"
# after_app_uninstall = "snrg.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "snrg.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
# override_doctype_class = {
# 	"Quotation": "snrg.overrides.CustomQuotation"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }
doc_events = {
    "Customer": {
        "before_save": [
            "snrg.snrg.doctype.counter.counter.insert_or_update_document",
            "snrg.doc_events.validate_gstin",
        ],
    },
    "Lead": {
        "before_save": [
            "snrg.snrg.doctype.counter.counter.insert_or_update_document",
            "snrg.doc_events.validate_gstin",
        ],
        "on_update": "snrg.doc_events.create_address"
    },
    "Secondary Customer": {
        "before_save": [
            "snrg.snrg.doctype.counter.counter.insert_or_update_document",
            "snrg.doc_events.validate_gstin",
        ],
        "on_update": "snrg.doc_events.create_address_and_contact"
    },
    "Supplier": {
        "before_save": "snrg.doc_events.validate_gstin",
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"snrg.tasks.all"
# 	],
# 	"daily": [
# 		"snrg.tasks.daily"
# 	],
# 	"hourly": [
# 		"snrg.tasks.hourly"
# 	],
# 	"weekly": [
# 		"snrg.tasks.weekly"
# 	],
# 	"monthly": [
# 		"snrg.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "snrg.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "snrg.event.get_events"
# }

override_whitelisted_methods = {
	"erpnext.selling.doctype.quotation.quotation.make_sales_order": "snrg.overrides.make_sales_order",
    "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice": "snrg.overrides.make_sales_invoice"
}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "snrg.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["snrg.utils.before_request"]
# after_request = ["snrg.utils.after_request"]

# Job Events
# ----------
# before_job = ["snrg.utils.before_job"]
# after_job = ["snrg.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"snrg.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
