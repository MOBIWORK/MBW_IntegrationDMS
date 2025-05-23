# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách nhà cung cấp
def sync_provider():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.provider.sync_provider_job", queue="long", timeout=300, key = KEY_REALTIME["key_realtime_categories"])
        return {"message": "Provider Sync job has been queued."}

def sync_provider_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Provider sync job started.")

        # Lấy danh sách provider chưa đồng bộ
        providers = frappe.get_all(
            "Supplier",
            filters={"is_sync": False},
            fields=["name", "supplier_name", "is_sync"]
        )

        if not providers:
            create_dms_log(status="Skipped", message="No new provider to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new provider to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["supplier_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in providers
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Provider",
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
            for ct in providers:
                frappe.db.set_value("Supplier", {"name": ct["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Provider synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], "Provider synced successfully.", done=True)
            return {"message": "Provider synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync provider."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], "Failed to sync provider.", error=True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing provider.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    
def update_status_after_change(doc, method):
    doc.is_sync = 0