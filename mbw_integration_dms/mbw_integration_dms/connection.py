# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
import json
import base64
from frappe import _

from mbw_integration_dms.mbw_integration_dms.constants import (
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
 

@frappe.whitelist()
def store_request_data() -> None:
    """Nhận request từ đối tác, xác thực Basic Auth và xử lý dữ liệu."""
    if frappe.request:
        auth_header = frappe.get_request_header("Authorization")

        # Kiểm tra header Authorization
        if not auth_header or not auth_header.startswith("Basic "):
            frappe.throw(_("Missing or invalid Authorization header"))

        # Giải mã Basic Auth để lấy api_key và api_secret
        api_key, api_secret = _extract_basic_auth(auth_header)

        # Kiểm tra xác thực với dữ liệu trong settings
        _validate_request(api_key, api_secret, frappe.request)

        # Xử lý dữ liệu từ request
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
		timeout=30,
		is_async=True,
		data=data,
        request_id=log.name
	)


def _extract_basic_auth(auth_header):
    """Giải mã Basic Auth và trả về api_key và api_secret"""
    try:
        encoded_credentials = auth_header.split("Basic ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        api_key, api_secret = decoded_credentials.split(":", 1)
        return api_key, api_secret
    
    except Exception:
        frappe.throw(_("Invalid Basic Auth format"))

def _validate_request(api_key, api_secret, req):
    """Xác thực API key và secret với dữ liệu trong MBW Integration Settings"""
    settings = frappe.get_single("MBW Integration Settings")

    if settings.erp_api_key != api_key or settings.erp_api_secret != api_secret:
        create_dms_log(
            status="Error",
            request_data=req.data,
            message="Unauthorized API access attempt"
        )
        frappe.throw(_("Unauthorized API access"))
