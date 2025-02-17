# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.product import publish

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient

key_realtime_categories = "dms.key.sync.all.categories"
# Đồng bộ danh sách khu vực
def sync_region():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.region.sync_region_job", queue="long", timeout=300, key = key_realtime_categories)
    return {"message": "Region Sync job has been queued."}

def sync_region_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="region sync job started.")

        # Lấy danh sách region chưa đồng bộ
        regions = frappe.get_all(
            "Territory",
            filters={"is_sync": False},
            fields=["territory_name", "name", "is_sync"]
        )

        if not regions:
            create_dms_log(status="Skipped", message="No new region to sync.")
            publish(key_realtime_categories, "No new region to sync.", done = True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["territory_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in regions
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Region",
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
            for ct in regions:
                frappe.db.set_value("Territory", {"name": ct["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Region synced successfully."
            )
            publish(key_realtime_categories, "Region synced successfully.", done = True)
            return {"message": "Region synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync region."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(key_realtime_categories, f"Failed to sync: {response}", error = True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing region.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(key_realtime_categories, f"Sync Error: {str(e)}", error = True)
        return {"error": str(e)}