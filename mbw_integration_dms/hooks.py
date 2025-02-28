app_name = "mbw_integration_dms"
app_title = "MBW Integration DMS"
app_publisher = "MBW"
app_description = "app integration"
app_email = "mbw@gmail.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mbw_integration_dms/css/mbw_integration_dms.css"
# app_include_js = "/assets/mbw_integration_dms/js/mbw_integration_dms.js"

# include js, css files in header of web template
# web_include_css = "/assets/mbw_integration_dms/css/mbw_integration_dms.css"
# web_include_js = "/assets/mbw_integration_dms/js/mbw_integration_dms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mbw_integration_dms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mbw_integration_dms/public/icons.svg"

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
# 	"methods": "mbw_integration_dms.utils.jinja_methods",
# 	"filters": "mbw_integration_dms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mbw_integration_dms.install.before_install"
# after_install = "mbw_integration_dms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mbw_integration_dms.uninstall.before_uninstall"
# after_uninstall = "mbw_integration_dms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mbw_integration_dms.utils.before_app_install"
# after_app_install = "mbw_integration_dms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mbw_integration_dms.utils.before_app_uninstall"
# after_app_uninstall = "mbw_integration_dms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mbw_integration_dms.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Item": {
		"on_trash": "mbw_integration_dms.mbw_integration_dms.product.delete_product",
        "before_save": "mbw_integration_dms.mbw_integration_dms.product.check_uom_dms"
	},
    "Customer": {
        "on_trash": "mbw_integration_dms.mbw_integration_dms.customer.delete_customer"
    },
    "Sales Invoice": {
        "on_submit": "mbw_integration_dms.mbw_integration_dms.sales_invoice.create_sale_invoice"
    },
    "Delivery Note": {
        "on_submit": "mbw_integration_dms.mbw_integration_dms.delivery_note.create_delivery_note"
    },
    "Sales Order": {
        "on_cancel": "mbw_integration_dms.mbw_integration_dms.helpers.helpers.update_stt_so_cancel",
        "on_update_after_submit": "mbw_integration_dms.mbw_integration_dms.helpers.helpers.on_sales_order_update",
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "0 */6 * * *": [
            "mbw_integration_dms.mbw_integration_dms.kpi.get_kpi_dms",
            "mbw_integration_dms.mbw_integration_dms.timesheets.get_timesheet_dms",
        ]
    }
}

# Testing
# -------

# before_tests = "mbw_integration_dms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mbw_integration_dms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mbw_integration_dms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mbw_integration_dms.utils.before_request"]
# after_request = ["mbw_integration_dms.utils.after_request"]

# Job Events
# ----------
# before_job = ["mbw_integration_dms.utils.before_job"]
# after_job = ["mbw_integration_dms.utils.after_job"]

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
# 	"mbw_integration_dms.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["module", "in", ("MBW Integration DMS")]]
    },
    {
        "doctype": "Client Script",
        "filters": [["module", "in", ("MBW Integration DMS")]]
    },
    {
        "doctype": "Server Script",
        "filters": [["module", "in", ("MBW Integration DMS")]]
    },

]