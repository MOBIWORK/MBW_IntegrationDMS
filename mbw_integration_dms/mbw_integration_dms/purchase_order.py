# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
from frappe import _
from frappe.utils import nowdate
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import create_partner_log
from mbw_integration_dms.mbw_integration_dms.helpers.validators import validate_not_none


def create_purchase_order(data=None, **kwargs):
    """API tạo mới Purchase Order"""
    id_log_dms = data.get("id_log", None)

    try:
        # Lấy thông tin từ request
        supplier = validate_not_none(data.get("supplier"))
        items = data.get("items", [])

        # Kiểm tra supplier có tồn tại không
        if not frappe.db.exists("Supplier", supplier):
            frappe.throw(_("Supplier {0} does not exist").format(supplier))

        # Kiểm tra danh sách sản phẩm có hợp lệ không
        if not items:
            frappe.throw(_("Danh sách mục không được để trống"))

        valid_items = []
        for item in items:
            item_code = item.get("item_code")
            qty = item.get("qty")
            rate = item.get("rate")

            if not frappe.db.exists("Item", item_code):
                frappe.throw(_("Item {0} does not exist").format(item_code))

            if qty <= 0 or rate <= 0:
                frappe.throw(_("Số lượng và tỷ lệ phải lớn hơn 0 cho mặt hàng {0}").format(item_code))

            valid_items.append({
                "item_code": item_code,
                "qty": qty,
                "rate": rate,
            })

        # Ghi log trước khi tạo PO
        create_dms_log(
            status="Processing",
            request_data=data,
            message="Starting Purchase Order creation"
        )

        # Tạo mới Purchase Order
        purchase_order = frappe.get_doc({
            "doctype": "Purchase Order",
            "supplier": supplier,
            "schedule_date": nowdate(),
            "items": valid_items
        })
        purchase_order.insert(ignore_permissions=True)

        # Ghi log thành công
        create_dms_log(
            status="Success",
            request_data=data,
            response_data={"purchase_order_id": purchase_order.name},
            message="Purchase Order created successfully"
        )

        if id_log_dms:
            create_partner_log(
                id_log_dms=id_log_dms,
                status=True,
                title="Purchase Order create successfully.",
                message=f"Purchase Order {purchase_order.name} created successfully."
            )

        return {
            "status": "success",
            "message": "Purchase Order created successfully",
            "purchase_order_id": purchase_order.name
        }

    except Exception as e:
        # Ghi log lỗi nếu có vấn đề xảy ra
        create_dms_log(
            status="Failed",
            request_data=data,
            exception=e,
            rollback=True,
            message="Error occurred while creating Purchase Order"
        )

        if id_log_dms:
            create_partner_log(
                id_log_dms=id_log_dms,
                status=False,
                title="Error occurred while creating Purchase Order.",
                message=f"Error creating Purchase Order: {str(e)}"
            )

        frappe.db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }

