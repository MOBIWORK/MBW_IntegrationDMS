import frappe
import json
from frappe import _

from mbw_integration_dms.mbw_integration_dms.constants import (
	SETTING_DOCTYPE,
	EVENT_MAPPER
)

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log


def get_current_domain_name() -> str:
	"""Get current site domain name. E.g. test.erpnext.com

	If developer_mode is enabled and localtunnel_url is set in site config then domain  is set to localtunnel_url.
	"""
	if frappe.conf.developer_mode and frappe.conf.localtunnel_url:
		return frappe.conf.localtunnel_url
	else:
		return frappe.request.host


def get_callback_url() -> str:
	"""DMS calls this url when new events occur to subscribed webhooks.

	If developer_mode is enabled and localtunnel_url is set in site config then callback url is set to localtunnel_url.
	"""
	url = get_current_domain_name()

	return f"https://{url}/api/method/mbw_integration_dms.mbw_integration_dms.connection.store_request_data"
 

@frappe.whitelist(allow_guest=True)
def store_request_data() -> None:
	if frappe.request:
		hmac_header = frappe.get_request_header("X-ERP-JWT")

		_validate_request(frappe.request, hmac_header)

		data = json.loads(frappe.request.data)
		event = frappe.request.headers.get("X-ERP-Topic")

		return process_request(data, event)


def process_request(data, event):
	# Create log
	log = create_dms_log(method=EVENT_MAPPER[event], request_data=data)

	# Enqueue backround job
	frappe.enqueue(
		method=EVENT_MAPPER[event],
		queue="short",
		timeout=300,
		is_async=True,
		**{"payload": data, "request_id": log.name},
	)


def _validate_request(req, hmac_header):
	settings = frappe.get_doc(SETTING_DOCTYPE)
	secret_key = settings.dms_password

	if secret_key != hmac_header:
		create_dms_log(status="Error", request_data=req.data)
		frappe.throw(_("Unverified Webhook Data"))