# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
import pydash

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log

from mbw_integration_dms.mbw_integration_dms.helpers import configs
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_date, 
    validate_phone_number, 
    validate_choice,
    validate_not_none,
)

# Thêm mới đơn hàng
def create_sales_order(**kwargs):
    pass