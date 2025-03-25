# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách nhãn hiệu 
def sync_brand():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.brand.sync_brand_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Brand Sync job has been queued."}

def sync_brand_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Brand sync job started.")

        # Lấy danh sách Brand chưa đồng bộ
        brands = frappe.get_all(
            "Brand",
            filters={"is_sync": False},
            fields=["name", "brand", "is_sync"]
        )

        if not brands:
            create_dms_log(status="Skipped", message="No new brand to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new brand to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["brand"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in brands
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Brand",
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
            for ct in brands:
                frappe.db.set_value("Brand", {"name": ct["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Brand synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], "Brand synced successfully.", done=True)
            return {"message": "Brand synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync brand."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], f"Failed to sync: {response}", error=True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing brand.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}