# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


def create_sale_invoice(doc, method):
    try:
        dms_client = DMSApiClient()

        id_dms = doc.id_dms
        ma_don = doc.sales_order
        kho_hang = doc.set_warehouse
        ck_don = doc.discount_amount
        items = doc.items
        san_pham = []

        for i in items:
            item = {
                "ma_sp": i.item_code,
                "dvt": i.uom,
                "sl": i.qty,
                "don_gia": i.price_list_rate,
                "ck": i.discount_amount,
                "vat": 0,
                "ghi_chu": "",
                "is_km": i.is_free_item
            }
            san_pham.append(item)

        request_payload = {
            "orgid": dms_client.orgid,
            "id_dms": id_dms,
            "ma_don": ma_don,
            "ck_don": ck_don,
            "kho_hang": kho_hang,
            "san_pham": san_pham
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/PublicAPI/sync_postSale",
            method="POST",
            body=request_payload
        )

        if response.get("status"):
            create_dms_log(
                status="Success",
                response_data=response,
                message="PBH create successfully."
            )
            return {"message": "PBH create successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to create PBH."
            )
            frappe.logger().error(f"Failed to create: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while create PBH.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}
    

def add_sales_order(doc, method):
    items = doc.items
    so_name = None

    for i in items:
        so_name = i.sales_order

    if so_name:
        doc.sales_order = so_name
        so_id = frappe.get_value("Sales Order", so_name, "dms_so_id")
        doc.id_dms = so_id


@frappe.whitelist()
def get_remaining_qty(sales_order):
    so = frappe.get_doc("Sales Order", sales_order)
    remaining_items = []
    
    # Kiểm tra xem có sản phẩm khuyến mại nào không
    has_free_item = any(item.is_free_item for item in so.items)
    
    if not has_free_item:
        return []  # Không có sản phẩm khuyến mại, trả về danh sách rỗng

    for item in so.items:
        # Truy vấn số lượng đã lập hóa đơn
        billed_qty = frappe.db.sql("""
            SELECT SUM(qty) FROM `tabSales Invoice Item`
            WHERE sales_order = %s AND item_code = %s AND is_free_item = %s
        """, (sales_order, item.item_code, item.is_free_item))[0][0] or 0
        
        remaining_qty = item.qty - billed_qty

        if remaining_qty > 0:
            income_account = frappe.db.get_value(
                "Item Default", 
                {"parent": item.item_code, "company": so.company}, 
                "income_account"
            ) or frappe.get_value("Item Group", frappe.get_value("Item", item.item_code, "item_group"), "income_account") or \
            frappe.get_value("Company", so.company, "default_income_account")

            remaining_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "remaining_qty": remaining_qty,
                "rate": item.rate,
                "is_free_item": item.is_free_item,
                "income_account": income_account,
                "sales_order": sales_order
            })
    
    return remaining_items