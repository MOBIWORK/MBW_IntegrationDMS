# Copyright (c) 2025, Tuanbd mbwd
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.doctype.mbw_integration_log.mbw_integration_log import (
	create_log,
)
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient

from mbw_integration_dms.mbw_integration_dms.constants import (
	MODULE_NAME,
    SETTING_DOCTYPE
)

def create_dms_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)

def create_partner_log(id_log_dms, status, title, message=""):
    dms_client = DMSApiClient()

    payload = {
        "id": id_log_dms,
        "status": status,
        "title": title,
        "message": message
    }

    try:
        response = dms_client.request(
            endpoint="/sync_log",
            method="POST",
            body=payload
        )
        return response.json()
    
    except Exception as e:
        frappe.logger().error(f"Lỗi gửi log đến DMS: {str(e)}")
        return {"error": str(e)}