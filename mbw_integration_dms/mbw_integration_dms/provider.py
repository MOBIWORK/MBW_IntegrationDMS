# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


# Đồng bộ danh sách nhà cung cấp
def sync_provider():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.provider.sync_provider_job", queue="long", timeout=300)
    return {"message": "Provider Sync job has been queued."}

def sync_provider_job():
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
            endpoint="/CategorySync",
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
            return {"message": "Provider synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync provider."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing provider.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}