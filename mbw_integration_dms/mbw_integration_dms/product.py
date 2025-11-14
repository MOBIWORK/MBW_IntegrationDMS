# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe import _

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME
from mbw_integration_dms.mbw_integration_dms.utils import ( 
    create_dms_log,
    check_enable_integration_dms,
    check_auto_sync_product
)

enable_dms = check_enable_integration_dms()
check_sync_product = check_auto_sync_product()

# Đồng bộ danh sách sản phẩm
def sync_product():
    if enable_dms and check_sync_product:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.product.sync_product_job", queue="long", timeout=300, key = KEY_REALTIME["key_realtime_product"])
        return {"message": "Product Sync job has been queued."}

@frappe.whitelist()
def sync_product_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Product sync job started.")

        query = """
            SELECT 
                i.name, i.item_code, i.item_name, i.industry_dms, i.brand, i.description, i.stock_uom,
                it.item_tax_template, s.supplier as provider,

                (SELECT um.uom FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_even = 1 LIMIT 1) AS unit_even,
                (SELECT um.price_dms FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_even = 1 LIMIT 1) AS price_unit_even,
                (SELECT um.conversion_factor FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_even = 1 LIMIT 1) AS unit_even_conversion,

                (SELECT um.price_dms FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code 
                    ORDER BY um.unit_odd DESC, um.idx ASC LIMIT 1) AS price_unit_odd,
                (SELECT um.conversion_factor FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code 
                    ORDER BY um.unit_odd DESC, um.idx ASC LIMIT 1) AS unit_odd_conversion

            FROM `tabItem` i
            LEFT JOIN `tabItem Tax` it ON i.name = it.parent
            LEFT JOIN `tabItem Supplier` s ON i.name = s.parent
            WHERE 
                i.is_sale_dms = 1 
                AND i.is_sync = 0

            ORDER BY i.item_code
        """
        items = frappe.db.sql(query, as_dict=True)

        if not items:
            create_dms_log(status="Skipped", message="No new item to sync.")
            publish(KEY_REALTIME["key_realtime_product"], "No new item to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API client
        dms_client = DMSApiClient()

        total = len(items)
        success_count = 0
        fail_count = 0

        for idx, i in enumerate(items, start=1):
            payload = {
                "stt": idx,
                "ma_sp": i.get("item_code") or "",
                "ten_sp": i.get("item_name") or "",
                "nganh_hang": i.get("industry_dms") or "",
                "nha_cung_cap": i.get("provider") or "",
                "nhan_hieu": i.get("brand") or "",
                "dvt_chan": i.get("unit_even") or "",
                "dvt_le": i.get("stock_uom") or "",
                "ma_vach": "",
                "gia_le": i.get("price_unit_odd") or 0,
                "gia_chan": i.get("price_unit_even") or 0,
                "hsqd": i.get("unit_even_conversion") or 0,
                "gia_nhap": 1,
                "gia_nhap_le": 1,
                "vat": frappe.db.get_value(
                    "Item Tax Template Detail",
                    {"parent": i.get("item_tax_template")},
                    "tax_rate"
                ) if i.get("item_tax_template") else 0,
                "mo_ta": i.get("description") or ""
            }

            # Log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=payload,
                message=f"Syncing item {i['item_code']} ({idx}/{total})"
            )

            # Gửi dữ liệu qua API
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/Product",
                method="POST",
                body=payload
            )

            if success and response.get("status"):
                frappe.db.set_value("Item", i["name"], "is_sync", True, update_modified=False)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync item {i['item_code']}: {response}")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync item {i['item_code']}"
                )

        frappe.db.commit()

        summary_msg = f"Product sync completed. Success: {success_count}/{total}, Failed: {fail_count}/{total}"
        create_dms_log(
            status="Success" if fail_count == 0 else "Partial Success",
            message=summary_msg
        )
        publish(KEY_REALTIME["key_realtime_product"], summary_msg, done=True)

        return {"message": summary_msg}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing product.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_product"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    

# Xóa sản phẩm
def delete_product(doc, method):
    if enable_dms and check_sync_product:
        dms_client = DMSApiClient()

        # Xử lý chỉ xóa 1 hoặc nhiều sản phẩm
        item_codes = [doc.item_code] if isinstance(doc, frappe.model.document.Document) else doc

        # API yêu cầu ma là chuỗi, không phải danh sách
        codes_str = ";".join(item_codes)

        request_payload = {
            "ma": codes_str
        }

        create_dms_log(
            status="Processing",
            method="DELETE",
            request_data=request_payload,
            message=f"Sending delete request for products: {codes_str}"
        )

        try:
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/Product",
                method="DELETE",
                body=request_payload
            )

            if not success or not response.get("status"):
                frappe.throw(f"Không thể xóa sản phẩm bên DMS: {response.get('message', 'Lỗi không xác định')}")

            # Xóa sản phẩm trong ERPNext
            frappe.db.sql("DELETE FROM `tabItem` WHERE item_code IN %s", (item_codes,))
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message=f"Products deleted successfully from both ERPNext and DMS: {codes_str}"
            )

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Lỗi khi xóa sản phẩm: {str(e)}", "Product Deletion")
            frappe.throw(f"Lỗi khi xóa sản phẩm: {str(e)}")


# Check UOM DMS
def check_uom_dms(doc, method):
    if enable_dms and check_sync_product and doc.is_sale_dms:
        doc.is_sync = 0
        uoms_item = doc.uoms
        
        if uoms_item:
            for i in uoms_item:
                uom_detail = frappe.get_value("UOM", {"name": i.uom}, "is_sale_dms")
                if uom_detail == 0:
                    frappe.throw(f"Đơn vị tính {i.uom} không phải đơn vị bên DMS. Vui lòng chọn đơn vị tính của DMS để đồng bộ")