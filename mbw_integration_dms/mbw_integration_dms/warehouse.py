# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách kho hàng
def sync_warehouse():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.warehouse.sync_warehouse_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Warehouse Sync job has been queued."}

def sync_warehouse_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="warehouse sync job started.")

        # Lấy danh sách warehouse chưa đồng bộ
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"is_sync": False, "is_sale_dms": True, "disabled": False},
            fields=["warehouse_name", "name", "is_sync"]
        )

        if not warehouses:
            create_dms_log(status="Skipped", message="No new warehouse to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new warehouse to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["warehouse_name"],  # Tên danh mục
                "isActive": 1  # Trạng thái danh mục
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
            endpoint="/PublicAPI/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for ct in warehouses:
                frappe.db.set_value("Warehouse", {"name": ct["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Warehouse synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], "Warehouse synced successfully.", done=True)
            return {"message": "Warehouse synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync warehouse."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], f"Failed to sync: {response}", error=True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing warehouse.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    
def update_status_after_change(doc, method):
    if doc.is_sale_dms == 1:
        doc.is_sync = 0