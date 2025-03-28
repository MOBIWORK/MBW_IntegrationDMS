# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách ngành hàng
@frappe.whitelist(allow_guest=True)
def sync_industry():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.industry.sync_industry_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Industry Sync job has been queued."}

def sync_industry_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Industry sync job started.")

        # Lấy danh sách Industry chưa đồng bộ
        industrys = frappe.get_all(
            "DMS Industry",
            filters={"is_sync": False},
            fields=["industry_name", "industry_code", "is_sync"]
        )

        if not industrys:
            create_dms_log(status="Skipped", message="No new industry to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new industry to sync.", done = True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["industry_code"],  # Mã danh mục
                "name": ct["industry_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in industrys
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Industry",
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
            for ct in industrys:
                frappe.db.set_value("DMS Industry", {"name": ct["industry_name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Industry synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], "Industry synced successfully.", done=True)
            return {"message": "Industry synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync industry."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], f"Failed to sync: {response}", error = True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing industry.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error = True)
        return {"error": str(e)}