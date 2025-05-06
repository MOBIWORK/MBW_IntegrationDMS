# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
from frappe import _
import json

from mbw_integration_dms.mbw_integration_dms.utils import (
    create_dms_log
)
from mbw_integration_dms.mbw_integration_dms.helpers import configs
from mbw_integration_dms.mbw_integration_dms.customer import create_customers
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import create_partner_log
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_date, 
    validate_choice,
    validate_not_none,
)

# Tạo mới đơn hàng DMS to ERP
@frappe.whitelist(methods="POST")
def create_sale_order(data=None, **kwargs):
    if data:
        kwargs = data
    id_log_dms = kwargs.get("id_log", None)

    try:
        cus_name = None
        customer_code_dms = kwargs.get("customer")
        customer_name = frappe.get_value("Customer", {"customer_code_dms": customer_code_dms}, "name")
        customer_data = kwargs.get("customer_data", {})
        if customer_data:
            cus_name = customer_data.get("customer_name")

        # Kiểm tra nếu đơn hàng đã tồn tại với dms_so_id
        existing_order = frappe.db.exists("Sales Order", {"dms_so_id": kwargs.get("dms_so_id")})
        if existing_order:
            message = f"Sales Order {existing_order} already exists with dms_so_id {kwargs.get('dms_so_id')}"
    
            # Ghi log vào DMS
            create_dms_log(
                status="Skipped",
                request_data=kwargs,
                message=message
            )

            # Ghi log vào Partner log nếu có id_log_dms
            if id_log_dms:
                create_partner_log(
                    id_log_dms=id_log_dms,
                    status=False,
                    title="Sales Order Skipped",
                    message=message
                )
            return

        # Ghi log bắt đầu xử lý đơn hàng
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=kwargs,
            message=f"Processing Sales Order for customer {customer_code_dms}"
        )

        # Kiểm tra khách hàng có tồn tại không
        existing_customer = frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms})

        if not existing_customer:
            if not customer_data:
                frappe.throw(f"Khách hàng {customer_code_dms} chưa tồn tại và không có dữ liệu để tạo mới.")

            # Gọi hàm tạo khách hàng
            customers_list = [customer_data]
            create_customers(data={"customers": customers_list})

        new_order = frappe.new_doc("Sales Order")

        # Dữ liệu bắn lên để tạo sale order mới
        discount_amount_so = float(kwargs.get("discount_amount", 0))
        apply_discount_on = kwargs.get("apply_discount_on")
        promotions = kwargs.get("promotion_dms", [])

        sales_person = None
        user_mail = kwargs.get("email_employee")
        sales_person_name = frappe.get_value("Sales Person", {"email": user_mail}, "name")
        if sales_person_name:
            sales_person = sales_person_name
        else:
            employee = frappe.get_value("Employee", {"user_id": user_mail}, "name")
            sales_person = frappe.get_value("Sales Person", {"employee": employee}, "name")

        new_order.customer = validate_not_none(customer_name) if customer_name else validate_not_none(cus_name)
        new_order.dms_so_code = kwargs.get("dms_so_code")
        new_order.delivery_date = validate_date(kwargs.get("delivery_date") / 1000)
        new_order.set_warehouse = validate_not_none(kwargs.get("set_warehouse"))
        new_order.dms_so_code = kwargs.get("dms_so_code")
        new_order.dms_so_id = kwargs.get("dms_so_id")
        new_order.is_sale_dms = 1

        new_order.append("sales_team", {
            "sales_person": sales_person,
            "allocated_percentage": 100,
        })

        new_order.ignore_pricing_rule = 1

        # Thêm mới items trong đơn hàng
        items = kwargs.get("items", [])
        if not items or not isinstance(items, list):
            frappe.throw("Danh sách sản phẩm (items) không hợp lệ hoặc trống.")

        discount_amount_item = 0
        for item_data in items:
            is_free_item = item_data.get("is_free_item")
            discount_item = item_data.get("discount_amount", 0)
            discount_amount_item += discount_item

            new_order.append("items", {
                "item_code": item_data.get("item_code"),
                "qty": item_data.get("qty"),
                "uom": item_data.get("uom"),
                "custom_item_discount": discount_item,
                "price_list_rate": item_data.get("rate") if is_free_item == 0 else 0,
                "additional_notes": item_data.get("additional_notes"),
                "is_free_item": is_free_item
            })

        if apply_discount_on is not None:
            new_order.apply_discount_on = validate_choice(configs.discount_type)(apply_discount_on)
            new_order.discount_amount = discount_amount_so + discount_amount_item
        
        new_order.custom_order_discount = discount_amount_so
        new_order.custom_product_discount = discount_amount_item
        
        value_sp = ["SP_ST_SP", "TIEN_SP", "SP_SL_SP", "MUTI_SP_ST_SP", "MUTI_SP_SL_SP", "MUTI_TIEN_SP"]
        for promo in promotions:
            ptype = promo.get("ptype")
            # Nếu ptype là chuỗi JSON, thì parse
            if isinstance(ptype, str):
                ptype_data = json.loads(ptype)
            else:
                ptype_data = ptype
            ptype_label = ptype_data.get("label")
            ptype_value = ptype_data.get("value")

            product = promo.get("product")
            for item in product:
                if item.get("so_luong") > 0:
                    new_order.append("promotion_result", {
                        "promotion_id": promo.get("id"),
                        "promotion_name": promo.get("ten_khuyen_mai"),
                        "promotion_code": ptype_value,
                        "promotion_type": ptype_label,
                        "promotion_item_id": item.get("_id"),
                        "promotion_item_code": item.get("ma_san_pham"),
                        "promotional_item_name": item.get("ten_san_pham"),
                        "promotional_quantity": item.get("so_luong") if ptype_value in value_sp else 0,
                        "promotional_amount": item.get("so_luong") if ptype_value not in value_sp else 0
                    })

        new_order.insert()

        # Ghi log thành công
        create_dms_log(
            status="Success",
            request_data=kwargs,
            response_data={"sales_order": new_order.name},
            message=f"Sales Order {new_order.name} created successfully."
        )

        if id_log_dms:
            create_partner_log(
                id_log_dms=id_log_dms,
                status=True,
                title="Sales Order create successfully.",
                message=f"Sales Order {new_order.name} created successfully."
            )

        frappe.db.commit()
        return {"name": new_order.name}

    except Exception as e:
        frappe.logger().error(f"Lỗi tạo đơn hàng: {str(e)}")

        # Ghi log lỗi
        create_dms_log(
            status="Error",
            request_data=kwargs,
            message=f"Error creating Sales Order: {str(e)}"
        )

        if id_log_dms:
            create_partner_log(
                id_log_dms=id_log_dms,
                status=False,
                title="Sales Order create failed.",
                message=f"Error creating Sales Order: {str(e)}"
            )

        return {"error": str(e)}