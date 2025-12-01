# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
from frappe import _
import json
from datetime import datetime
import pytz
from frappe.utils import get_datetime, getdate
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log

# Tạo mới đơn hàng DMS to ERP
@frappe.whitelist()
def create_sale_order(**kwargs):
    try:
        payload = kwargs if isinstance(kwargs, dict) else json.loads(kwargs or "{}")

        if isinstance(payload.get("data"), list):
            if len(payload.get("data")) == 0:
                frappe.throw("Payload list is empty")
            payload = payload.get("data")[0]
        
        # Lấy dữ liệu chính
        customer_code = payload.get("ma_kh")
        customer_name = payload.get("ten_kh")
        sales_order_code = payload.get("ma_phieu")
        delivery_date = payload.get("ngay_giao")
        transaction_date = payload.get("ngay_dat")
        warehouse = payload.get("san_pham", [{}])[0].get("ma_kho_xuat")
        discount_order = float(payload.get("ck_don_hang") or 0)
        discount_product = float(payload.get("tong_ck_sp") or 0)
        sales_person = payload.get("ten_nguoi_dat")
        group_id = payload.get("ma_nhom")
        sales_person_code = payload.get("ma_nv_dat")

        customer = frappe.get_value("Customer", {"customer_code_dms": customer_code}, "name")
        if not customer:
            frappe.throw(f"Không tìm thấy khách hàng với mã {customer_code}")

        dt = to_gmt7(delivery_date)
        dt_tr = to_gmt7(transaction_date)
        new_order = frappe.new_doc("Sales Order")
        new_order.customer = customer
        new_order.customer_name = customer_name
        new_order.dms_so_code = sales_order_code
        new_order.delivery_date = dt.date()
        new_order.transaction_date = dt_tr.date()
        new_order.group_id = group_id
        new_order.sales_person_code = sales_person_code
        new_order.set_warehouse = warehouse
        new_order.is_sale_dms = 1
        new_order.ignore_pricing_rule = 1

        if frappe.db.exists("Sales Person", {"sales_person_name": sales_person}):
            sales_person = frappe.get_value("Sales Person", {"sales_person_name": sales_person}, "name")
            new_order.append("sales_team", {
                "sales_person": sales_person,
                "allocated_percentage": 100,
            })
        else:
            new_order.append("sales_team", {
                "sales_person": "Sales Team",
                "allocated_percentage": 100,
            })

        for item in payload.get("san_pham", []):
            new_order.append("items", {
                "item_code": item.get("ma_sp"),
                "qty": float(item.get("so_luong")),
                "uom": item.get("ten_dvt") or "Nos",
                "warehouse": item.get("ma_kho_xuat_km"),
                "price_list_rate": float(item.get("don_gia")) if item.get("don_gia") != "" else 0,
                "rate": float(item.get("don_gia")) if item.get("don_gia") != "" else 0,
                "custom_item_discount": float(item.get("chiet_khau")) or 0,
                "is_free_item": item.get("is_km") or 0,
                "additional_notes": item.get("ghi_chu")
            })

        for km in payload.get("san_pham_km", []):
            new_order.append("items", {
                "item_code": km.get("ma_sp_km"),
                "qty": float(km.get("so_luong_km") or 0),
                "uom": km.get("ten_dvt_km") or "Nos",
                "warehouse": km.get("ma_kho_xuat_km"),
                "rate": 0,
                "price_list_rate": 0,
                "is_free_item": 1,
                "additional_notes": km.get("ghi_chu_km")
            })

        # Thêm sản phẩm khuyến mãi
        if payload.get("promotion"):
            for item_km in payload.get("promotion", []):
                # product có thể là danh sách (nhiều sản phẩm khuyến mãi)
                for prod in item_km.get("product", []):
                    new_order.append("promotion_result", {
                        "promotion_id": item_km.get("id"),
                        "promotion_name": item_km.get("ten_khuyen_mai"),
                        "promotion_type": frappe.parse_json(item_km.get("ptype")).get("value") if item_km.get("ptype") else "",
                        "promotion_code": payload.get("ma_phieu"),
                        "promotion_item_id": prod.get("_id"),
                        "promotion_item_code": prod.get("ma_san_pham"),
                        "promotional_item_name": prod.get("ten_san_pham"),
                        "promotional_quantity": prod.get("so_luong") or 0,
                        "promotional_amount": 0
                    })

        total_discount = discount_order + discount_product
        if total_discount > 0:
            new_order.apply_discount_on = "Grand Total"
            new_order.discount_amount = total_discount
        
        new_order.insert(ignore_permissions=True)
        frappe.db.commit()

        create_dms_log(
            status="Success",
            request_data=payload,
            response_data={"sales_order": new_order.name},
            message=f"Tạo Sales Order thành công: {new_order.name}"
        )

        frappe.response["status"] = "ok"
        frappe.response["name"] = new_order.name
        return

    except Exception as e:
        frappe.db.rollback()
        create_dms_log(
            status="Error",
            request_data=kwargs,
            message=f"Lỗi tạo Sales Order: {str(e)}"
        )
        return {"error": str(e)}
    

def to_gmt7(dt_str):
    if not dt_str:
        return None
    utc_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    gmt7 = pytz.timezone("Asia/Ho_Chi_Minh")
    return utc_dt.astimezone(gmt7)