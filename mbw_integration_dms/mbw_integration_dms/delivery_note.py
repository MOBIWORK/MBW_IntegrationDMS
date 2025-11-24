# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms


def create_delivery_note(doc, method):
    enable_dms = check_enable_integration_dms()

    if enable_dms:
        try:
            dms_client = DMSApiClient()

            ma_don_erp = doc.sales_order
            ma_don_dms = frappe.get_value("Sales Order", {"name": ma_don_erp}, "dms_so_code")
            kho_hang = doc.set_warehouse
            ck_don = doc.discount_amount
            ma_kh = doc.customer
            items = doc.items
            ngay_xuat = doc.posting_date
            tong_tien_hang = doc.total
            phai_thanh_toan = doc.grand_total
            tong_vat = doc.total_taxes_and_charges
            san_pham = []

            for i in items:
                item = {
                    "ma_sp": i.item_code,
                    "ma_dvt": i.uom,
                    "so_luong": i.qty,
                    "don_gia": i.rate,
                    "chiet_khau_sp": i.discount_amount,
                    "vat": 0,
                    "ghi_chu": "",
                }
                san_pham.append(item)

            request_payload = {
                "ma_don_lien_quan": ma_don_dms,
                "ckdh": ck_don,
                "kho_xuat": kho_hang,
                "ma_kh": ma_kh,
                "ngay_xuat": ngay_xuat.strftime("%Y-%m-%d"),
                "tong_tien_hang": tong_tien_hang,
                "tong_vat": tong_vat,
                "phai_thanh_toan": phai_thanh_toan,
                "dien_giai": "ERP Delivery Note",
                "nha_cung_cap":"",
                "kho_nhap": "",
                "data_san_pham": san_pham
            }

            # Ghi log request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi dữ liệu qua API DMS
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/InventoryExportCustomer",
                method="POST",
                body=request_payload
            )

            if response.get("status"):
                create_dms_log(
                    status="Success",
                    response_data=response,
                    message="PXK create successfully."
                )
                return {"message": "PXK create successfully."}
            else:
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message="Failed to create PXK."
                )
                frappe.logger().error(f"Failed to create: {response}")
                return {"error": response}

        except Exception as e:
            create_dms_log(
                status="Error",
                exception=str(e),
                message="Exception occurred while create PXK.",
                rollback=True
            )
            frappe.logger().error(f"Sync Error: {str(e)}")
            return {"error": str(e)}
    

def add_sales_order(doc, method):
    items = doc.items
    so_name = None

    for i in items:
        so_name = i.against_sales_order

    if so_name:
        doc.sales_order = so_name
        so_code = frappe.get_value("Sales Order", so_name, "dms_so_code")
        doc.id_dms = so_code