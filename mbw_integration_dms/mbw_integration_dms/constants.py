# Copyright (c) 2025, Tuanbd mbwd

MODULE_NAME = "MBW Integration DMS"
SETTING_DOCTYPE = "MBW Integration Settings"

API_VERSION = "2025-01"

WEBHOOK_EVENTS = [
	"orders/create",
	"orders/paid",
	"orders/cancelled",
]

EVENT_MAPPER = {
	"orders/create": "",
	"orders/paid": "",
	"orders/cancelled": "",
}