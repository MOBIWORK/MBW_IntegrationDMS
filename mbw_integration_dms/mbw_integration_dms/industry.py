# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách ngành hàng
def sync_industry():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.industry.sync_industry_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Industry Sync job has been queued."}
    
def sync_industry_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Industry sync job started.")

        # Lấy danh sách Industry chưa đồng bộ
        industries = frappe.get_all(
            "DMS Industry",
            filters={"is_sync": False},
            fields=["industry_name", "industry_code", "is_sync"]
        )

        if not industries:
            create_dms_log(status="Skipped", message="No new industry to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new industry to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        success_count = 0
        fail_count = 0

        # Lặp từng industry và gửi riêng lẻ
        for idx, ct in enumerate(industries, start=1):
            request_payload = {
                "stt": idx,
                "ma": ct["industry_code"],   # Mã danh mục
                "ten": ct["industry_name"],  # Tên danh mục
                "trang_thai": True           # Mặc định True
            }

            # Ghi log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi dữ liệu qua API DMS
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/ItemIndustry",
                method="POST",
                body=request_payload
            )

            # Kiểm tra phản hồi
            if response.get("status"):
                frappe.db.set_value("DMS Industry", {"industry_code": ct["industry_code"]}, "is_sync", True)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync industry {ct['industry_code']}: {response}")

        frappe.db.commit()

        # Tổng kết kết quả
        message = f"Industry sync done. Success: {success_count}, Failed: {fail_count}"
        status = "Success" if fail_count == 0 else "Partial Success"

        create_dms_log(
            status=status,
            message=message
        )
        publish(KEY_REALTIME["key_realtime_categories"], message, done=True)

        return {"message": message}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing industry.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}