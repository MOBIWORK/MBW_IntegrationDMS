# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

MODULE_NAME = "MBW Integration DMS"
SETTING_DOCTYPE = "MBW Integration Settings"

API_VERSION = "2025-01"

WEBHOOK_EVENTS = []

EVENT_MAPPER = {
	"customers_create": "mbw_integration_dms.mbw_integration_dms.customer.create_customers",
    "sales_order_create": "mbw_integration_dms.mbw_integration_dms.sales_order.create_sale_order",
    "sales_order_delete": "mbw_integration_dms.mbw_integration_dms.sales_order.cancel_sale_order",
}