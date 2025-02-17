# Copyright (c) 2025, Tuanbd mbwd
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.doctype.mbw_integration_log.mbw_integration_log import (
	create_log,
)

from mbw_integration_dms.mbw_integration_dms.constants import (
	MODULE_NAME
)

def create_dms_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)