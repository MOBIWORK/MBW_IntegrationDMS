import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


# Đồng bộ danh sách sản phẩm
def sync_product():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.product.sync_product_job", queue="long", timeout=300)
    return {"message": "Product Sync job has been queued."}

def sync_product_job():
    try:
        create_dms_log(status="Queued", message="Brand sync job started.")

        query = """
            SELECT 
                i.name, i.item_code, i.item_name, i.industry, i.brand, i.description,
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
                "conversion_rate": i["unit_odd_conversion"],
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
            endpoint="/ProductSync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if success:
            for i in items:
                frappe.db.set_value("Item", {"name": i["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Item synced successfully."
            )
            return {"message": "Item synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync item."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing item.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}
    

# Xóa sản phẩm
def delete_product(doc, method):
    dms_client = DMSApiClient()

    


