# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from datetime import datetime
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms


@frappe.whitelist()
def create_sale_invoice(doc, method):
    enable_dms = check_enable_integration_dms()

    if not enable_dms:
        return

    try:
        dms_client = DMSApiClient()

        # Lấy dữ liệu chính từ doc
        ma_phieu = doc.name
        ma_phieu_dat = doc.sales_order or ""
        ma_nhom = doc.group_id or ""
        ma_nv_dat = doc.sales_person_code or ""
        ma_kh = getattr(doc, "customer", "")
        ma_kh_dms = frappe.get_value("Customer", ma_kh, "customer_code_dms") if ma_kh else ""
        ten_kh = frappe.get_value("Customer", ma_kh, "customer_name") if ma_kh else ""
        sdt = frappe.get_value("Customer", ma_kh, "mobile_no") or ""
        dia_chi = frappe.get_value("Customer", ma_kh, "customer_primary_address") or ""
        dien_giai = doc.remarks or ""
        ngay_dat = ngay_dat = format_date_safe(doc.posting_date)
        tong_tien_hang = doc.total or 0
        tong_tien_vat = doc.total_taxes_and_charges or 0
        tong_ck_sp = sum([i.discount_amount for i in doc.items if not i.is_free_item]) or 0
        ck_don_hang = doc.discount_amount or 0
        phai_thanh_toan = doc.grand_total or 0

        # Xử lý bảng con items
        san_pham = []
        san_pham_km = []

        for i in doc.items:
            # Lấy % VAT từ Item Tax Template (nếu có)
            vat_rate = 0
            if i.item_tax_template:
                tax_details = frappe.get_all(
                    "Item Tax Template Detail",
                    filters={"parent": i.item_tax_template},
                    fields=["tax_rate"],
                    limit=1
                )
                if tax_details:
                    vat_rate = tax_details[0].tax_rate or 0

            item_data = {
                "ma_sp": i.item_code,
                "ma_dvt": i.uom,
                "vat": vat_rate,
                "so_luong": i.qty,
                "ma_kho_xuat": i.warehouse or doc.set_warehouse,
                "don_gia": i.rate,
                "chiet_khau_sp": i.discount_amount or 0,
                "ghi_chu": i.description or ""
            }

            if i.is_free_item:
                san_pham_km.append({
                    "ma_sp_km": i.item_code,
                    "ma_dvt_km": i.uom,
                    "ma_kho_xuat_km": i.warehouse or doc.set_warehouse,
                    "so_luong_km": i.qty,
                    "promotion": {},
                    "ghi_chu_km": i.description or ""
                })
            else:
                san_pham.append(item_data)

        # Build payload
        request_payload = {
            "trang_thai": "Đã bán hàng",
            "ma_phieu": ma_phieu,
            "ma_phieu_dat": ma_phieu_dat,
            "ma_nhom": ma_nhom,
            "ma_nv_dat": ma_nv_dat,
            "ma_kh": ma_kh_dms,
            "ten_kh": ten_kh,
            "sdt": sdt,
            "dia_chi": dia_chi,
            "ngay_dat": ngay_dat,
            "dien_giai": dien_giai,
            "tong_tien_hang": tong_tien_hang,
            "tong_tien_vat": tong_tien_vat,
            "tong_ck_sp": tong_ck_sp,
            "ck_don_hang": ck_don_hang,
            "phai_thanh_toan": phai_thanh_toan,
            "san_pham": san_pham,
            "san_pham_km": san_pham_km
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi request qua DMS API
        response, success = dms_client.request(
            endpoint="/OpenAPI/V1/Bill",
            method="POST",
            body=request_payload
        )

        # Log kết quả
        if response.get("status"):
            create_dms_log(
                status="Success",
                response_data=response,
                message="Hóa đơn (PBH) tạo thành công."
            )
            return {"message": "PBH create successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Tạo PBH thất bại."
            )
            frappe.logger().error(f"Failed to create PBH: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while creating PBH.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}


def format_date_safe(d):
    if not d:
        return ""
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
    return d.strftime("%d/%m/%Y")


def add_sales_order(doc, method):
    # Lấy SO đầu tiên trong items
    so_name = next((i.sales_order for i in doc.items if i.sales_order), None)
    if not so_name:
        return

    # Gán SO vào header
    doc.sales_order = so_name

    # Gán các field header
    so_fields = frappe.db.get_value(
        "Sales Order", so_name,
        ["dms_so_id", "group_id", "sales_person_code"],
        as_dict=True
    )

    if so_fields:
        doc.id_dms = so_fields.dms_so_id
        doc.group_id = so_fields.group_id
        doc.sales_person_code = so_fields.sales_person_code

    # Lấy toàn bộ item rows của SO
    so_items = frappe.get_all(
        "Sales Order Item",
        filters={"parent": so_name},
        fields=["name", "item_code", "idx"]
    )

    so_map = {}
    for row in so_items:
        so_map.setdefault(row.item_code, []).append(row)

    for key in so_map:
        so_map[key].sort(key=lambda r: r.idx)

    usage_counter = {}

    for item in doc.items:
        if not item.item_code:
            continue

        if item.item_code not in so_map:
            continue

        # Lấy dòng kế tiếp theo thứ tự
        usage_counter.setdefault(item.item_code, 0)
        index = usage_counter[item.item_code]

        if index < len(so_map[item.item_code]):
            item.so_detail = so_map[item.item_code][index].name
            usage_counter[item.item_code] += 1


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