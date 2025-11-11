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

        success_count = 0
        fail_count = 0

        # Lặp từng brand và gửi từng request riêng
        for idx, ct in enumerate(brands, start=1):
            request_payload = {
                "stt": idx,
                "ma": ct["name"],
                "ten": ct["brand"],
                "trang_thai": True
            }

            # Ghi log request từng brand
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi từng brand
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/ItemBrand",
                method="POST",
                body=request_payload
            )

            if response.get("status"):
                frappe.db.set_value("Brand", ct["name"], "is_sync", True)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync brand {ct['name']}: {response}")

        frappe.db.commit()

        # Ghi log kết quả tổng
        message = f"Brand sync done. Success: {success_count}, Failed: {fail_count}"
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
            message="Exception occurred while syncing brand.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    
def update_status_after_change(doc, method):
    doc.is_sync = 0