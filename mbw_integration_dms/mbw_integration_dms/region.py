# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách khu vực
def sync_region():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.region.sync_region_job", queue="long", timeout=300, key = KEY_REALTIME["key_realtime_categories"])
        return {"message": "Region Sync job has been queued."}

@frappe.whitelist()
def sync_region_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Region sync job started.")

        # Lấy danh sách region chưa đồng bộ
        regions = frappe.get_all(
            "Territory",
            filters={"is_sync": False},
            fields=["territory_name", "name", "is_sync"]
        )

        if not regions:
            create_dms_log(status="Skipped", message="No new region to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new region to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        total = len(regions)
        success_count = 0
        fail_count = 0

        # Gửi từng bản ghi một (thay vì gửi mảng)
        for idx, ct in enumerate(regions, start=1):
            single_payload = {
                "stt": idx,
                "ma": ct["name"],  # Mã danh mục
                "ten": ct["territory_name"],  # Tên danh mục
                "trang_thai": True
            }

            # Ghi log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=single_payload
            )

            # Gửi dữ liệu đến DMS
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/CustomerRegion",
                method="POST",
                body=single_payload
            )

            # Kiểm tra phản hồi
            if success and response.get("status"):
                frappe.db.set_value("Territory", ct["name"], "is_sync", True, update_modified=False)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync region {ct['territory_name']}: {response}")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync region {ct['territory_name']}."
                )

        frappe.db.commit()

        # Tổng kết kết quả
        summary_msg = f"Region sync completed. Success: {success_count}/{total}, Failed: {fail_count}/{total}"
        create_dms_log(status="Success" if fail_count == 0 else "Partial Success", message=summary_msg)
        publish(KEY_REALTIME["key_realtime_categories"], summary_msg, done=True)

        return {"message": summary_msg}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing region.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    
def update_status_after_change(doc, method):
    doc.is_sync = 0