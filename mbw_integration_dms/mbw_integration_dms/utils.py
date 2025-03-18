# Copyright (c) 2025, Tuanbd mbwd
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.doctype.mbw_integration_log.mbw_integration_log import (
	create_log,
)

from mbw_integration_dms.mbw_integration_dms.constants import (
	MODULE_NAME,
	SETTING_DOCTYPE
)

def create_dms_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)

def check_enable_integration_dms():
	company = frappe.defaults.get_user_default("company")
	company_settings = frappe.get_doc(SETTING_DOCTYPE, {"name": company})
	enable_dms = company_settings.enable_dms
	return enable_dms

def check_auto_sync_product():
	company = frappe.defaults.get_user_default("company")
	company_settings = frappe.get_doc(SETTING_DOCTYPE, {"name": company})
	auto_sync_product = company_settings.auto_sync_product
	return auto_sync_product