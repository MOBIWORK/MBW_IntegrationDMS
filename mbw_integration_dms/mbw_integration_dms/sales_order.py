# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.customer import create_customers
from mbw_integration_dms.mbw_integration_dms.helpers import configs
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_date, 
    validate_choice,
    validate_not_none,
)

# Tạo mới đơn hàng
@frappe.whitelist(methods="POST")
def create_sale_order(**kwargs):
    try:
        kwargs = frappe._dict(kwargs)
        customer_code_dms = kwargs.get("customer")

        # Ghi log bắt đầu xử lý đơn hàng
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=kwargs,
            message=f"Processing Sales Order for customer {customer_code_dms}"
        )

        # 🛠 Kiểm tra khách hàng có tồn tại không
        existing_customer = frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms})

        if not existing_customer:
            customer_data = kwargs.get("customer_data", {})
            if not customer_data:
                frappe.throw(f"Khách hàng {customer_code_dms} chưa tồn tại và không có dữ liệu để tạo mới.")

            # Gọi hàm tạo khách hàng
            create_customer_result = create_customers(data=[customer_data])

            if create_customer_result.get("results", [{}])[0].get("status") != "Success":
                frappe.throw(f"Không thể tạo khách hàng {customer_code_dms}: {create_customer_result}")

        new_order = frappe.new_doc("Sales Order")

        # Dữ liệu bắn lên để tạo sale order mới
        discount_amount = float(kwargs.get("discount_amount", 0))
        apply_discount_on = kwargs.get("apply_discount_on")
        id_log_dms = kwargs.get("id_log")

        new_order.customer = validate_not_none(customer_code_dms)
        new_order.dms_so_code = kwargs.get("dms_so_code")
        new_order.delivery_date = validate_date(kwargs.delivery_date)  # Ngày giao
        new_order.set_warehouse = validate_not_none(kwargs.get("set_warehouse"))  # Kho hàng

        if apply_discount_on is not None:
            new_order.apply_discount_on = validate_choice(configs.discount_type)(apply_discount_on)
            new_order.discount_amount = discount_amount

        new_order.ignore_pricing_rule = 1

        # Thêm mới items trong đơn hàng
        items = kwargs.get("items", [])
        if not items or not isinstance(items, list):
            frappe.throw("Danh sách sản phẩm (items) không hợp lệ hoặc trống.")

        for item_data in items:
            discount_percentage = float(item_data.get("discount_amount", 0))

            new_order.append("items", {
                "item_code": item_data.get("item_code"),
                "qty": item_data.get("qty"),
                "uom": item_data.get("uom"),
                "rate": item_data.get("rate"),
                "discount_amount": discount_percentage,
                "additional_notes": item_data.get("additional_notes"),
                "is_free_item": item_data.get("is_free_item")
            })

        new_order.insert()
        frappe.db.commit()

        # Ghi log thành công
        create_dms_log(
            status="Success",
            request_data=kwargs,
            response_data={"sales_order": new_order.name},
            message=f"Sales Order {new_order.name} created successfully."
        )

        return {"name": new_order.name}

    except Exception as e:
        frappe.logger().error(f"Lỗi tạo đơn hàng: {str(e)}")

        # Ghi log lỗi
        create_dms_log(
            status="Failed",
            request_data=kwargs,
            message=f"Error creating Sales Order: {str(e)}"
        )

        return {"error": str(e)}