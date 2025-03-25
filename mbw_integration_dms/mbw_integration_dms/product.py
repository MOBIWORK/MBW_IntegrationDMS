# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe import _

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import ( 
    create_dms_log,
    check_enable_integration_dms,
    check_auto_sync_product
)
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()
check_sync_product = check_auto_sync_product()

# Đồng bộ danh sách sản phẩm
def sync_product():
    if enable_dms and check_sync_product:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.product.sync_product_job", queue="long", timeout=300, key = KEY_REALTIME["key_realtime_product"])
        return {"message": "Product Sync job has been queued."}

def sync_product_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Brand sync job started.")

        query = """
            SELECT 
                i.name, i.item_code, i.item_name, i.industry, i.brand, i.description, i.stock_uom,
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
            publish(KEY_REALTIME["key_realtime_product"], "No new item to sync.", done= True)
            return {"message": "No new data to sync."}
        
        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": i["item_code"],
                "name": i["item_name"],
                "industry": i["industry"],
                "provider": i["provider"],
                "brand": i["brand"],
                "unit_even": i["unit_even"],
                "unit_odd": i["stock_uom"],
                "gia_le": i["price_unit_odd"],
                "gia": i["price_unit_even"],
                "conversion_rate": i["unit_even_conversion"],
                "tax": frappe.db.get_value("Item Tax Template Detail", {"parent": i.get("item_tax_template")}, "tax_rate") if i.get("item_tax_template") else 0,
                "description": i["description"]
            }
            for i in items
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "orgid": dms_client.orgid,
            "data": formatted_data
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/PublicAPI/ProductSync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for i in items:
                frappe.db.set_value("Item", {"name": i["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Item synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_product"],"Item synced successfully.", done=True)
            return {"message": "Item synced successfully."}
        else:
            error_message = response.get("message", "Failed to sync item.")
            errors_detail = response.get("errorsmsg", [])

            create_dms_log(
                status="Failed",
                response_data=response,
                message=f"Failed to sync item: {error_message}. Errors: {', '.join(errors_detail)}"
            )

            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_product"] ,f"Failed to sync: {response}", error=True)
            return {"error": error_message, "details": errors_detail}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing item.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_product"],f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    

# Xóa sản phẩm
def delete_product(doc, method):
    """Xóa sản phẩm khỏi ERPNext nếu xóa thành công bên DMS"""
    if enable_dms and check_sync_product:
        dms_client = DMSApiClient()

        # Nếu chỉ xóa 1 sản phẩm, convert thành danh sách
        item_codes = [doc.item_code] if isinstance(doc, frappe.model.document.Document) else doc

        request_payload = {
            "orgid": dms_client.orgid,
            "data": item_codes
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload,
            message=f"Sending delete request for products: {', '.join(item_codes)}"
        )

        try:
            # Gửi request xóa sản phẩm đến API DMS
            response, success = dms_client.request(
                endpoint="/ProductDel",
                method="POST",
                body=request_payload
            )

            # Nếu API đối tác trả về lỗi, không xóa sản phẩm bên ERPNext
            if not success or not response.get("status"):
                frappe.throw(f"Không thể xóa sản phẩm bên DMS: {response.get('message', 'Lỗi không xác định')}")

            # Nếu thành công, xóa sản phẩm trong ERPNext
            frappe.db.sql("DELETE FROM `tabItem` WHERE item_code IN %s", (item_codes,))
            frappe.db.commit()

            # Ghi log thành công
            create_dms_log(
                status="Success",
                response_data=response,
                message=f"Products deleted successfully from both ERPNext and DMS: {', '.join(item_codes)}"
            )

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Lỗi khi xóa sản phẩm: {str(e)}", "Product Deletion")
            frappe.throw(f"Lỗi khi xóa sản phẩm: {str(e)}")


# Check UOM DMS
def check_uom_dms(doc, method):
    if enable_dms and check_sync_product and doc.is_sale_dms:
        uoms_item = doc.uoms
        
        if uoms_item:
            for i in uoms_item:
                uom_detail = frappe.get_value("UOM", {"name": i.uom}, "is_sale_dms")
                if uom_detail == 0:
                    frappe.throw(f"Đơn vị tính {i.uom} không phải đơn vị bên DMS. Vui lòng chọn đơn vị tính của DMS để đồng bộ")