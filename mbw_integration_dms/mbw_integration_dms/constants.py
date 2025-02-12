# Copyright (c) 2025, TuanBD MBWD

MODULE_NAME = "MBW Integration DMS"
SETTING_DOCTYPE = "MBW Integration Settings"

API_VERSION = "2025-01"

WEBHOOK_EVENTS = []

EVENT_MAPPER = {
	"customers_create": "mbw_integration_dms.mbw_integration_dms.customer.create_customers",
    "customers_update": "mbw_integration_dms.mbw_integration_dms.customer.update_customer",
    "sales_order_create": "",
    "sales_order_delete": "",
}