import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


# Đồng bộ danh sách kho hàng
def sync_warehouse():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.warehouse.sync_warehouse_job", queue="long", timeout=300)
    return {"message": "Warehouse Sync job has been queued."}

def sync_warehouse_job():
    try:
        create_dms_log(status="Queued", message="warehouse sync job started.")

        # Lấy danh sách warehouse chưa đồng bộ
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"is_sync": False},
            fields=["warehouse_name", "name", "disabled", "is_sync"]
        )

        if not warehouses:
            create_dms_log(status="Skipped", message="No new warehouse to sync.")
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["warehouse_name"],  # Tên danh mục
                "isActive": ct["disabled"]  # Trạng thái danh mục
            }
            for ct in warehouses
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Warehouse",
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
            endpoint="/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if success:
            for ct in warehouses:
                frappe.db.set_value("Warehouse", ct["name"], "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Warehouse synced successfully."
            )
            return {"message": "Warehouse synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync warehouse."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing warehouse.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}