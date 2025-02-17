# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe import _

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient

key_realtime_product = "dms.key.sync.all.products"
# Đồng bộ danh sách sản phẩm
def sync_product():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.product.sync_product_job", queue="long", timeout=300, key = key_realtime_product)
    return {"message": "Product Sync job has been queued."}

def sync_product_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Brand sync job started.")

        query = """
            SELECT 
                i.name, i.item_code, i.item_name, i.industry, i.brand, i.description, i.standard_rate,
                it.item_tax_template, s.supplier as provider,

                (SELECT um.uom FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_even = 1 LIMIT 1) AS unit_even,
                (SELECT um.conversion_factor FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_even = 1 LIMIT 1) AS unit_even_conversion,

                (SELECT um.uom FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_odd = 1 LIMIT 1) AS unit_odd,
                (SELECT um.conversion_factor FROM `tabUOM Conversion Detail` um 
                    WHERE um.parent = i.item_code AND um.unit_odd = 1 LIMIT 1) AS unit_odd_conversion

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
            publish(key_realtime_product, "No new item to sync.", done= True)
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
                "unit_odd": i["unit_odd"],
                "gia_le": i["standard_rate"],
                "gia": i["standard_rate"] * i["unit_even_conversion"],
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
            publish(key_realtime_product,"Item synced successfully.", done=True)
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
            publish(key_realtime_product ,f"Failed to sync: {response}", error=True)
            return {"error": error_message, "details": errors_detail}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing item.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(key_realtime_product,f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    

# Xóa sản phẩm
def delete_product(doc, method):
    """Xóa sản phẩm khỏi ERPNext nếu xóa thành công bên DMS"""
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

def publish(key, message, synced=False, error=False, done=False, br=True):
    frappe.publish_realtime(
		key,
		{
			"synced": synced,
			"error": error,
			"message": message + ("<br /><br />" if br else ""),
			"done": done,
		},
	)