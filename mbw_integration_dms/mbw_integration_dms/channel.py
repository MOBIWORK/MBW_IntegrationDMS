# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách kênh
def sync_channel():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.channel.sync_channel_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Channel Sync job has been queued."}

@frappe.whitelist()
def sync_channel_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Channel sync job started.")

        # Lấy danh sách Channel chưa đồng bộ
        channels = frappe.get_all(
            "Channel",
            filters={"is_sync": False},
            fields=["channel_name", "channel_code", "is_sync"]
        )

        if not channels:
            create_dms_log(status="Skipped", message="No new channel to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new data to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        success_count = 0
        fail_count = 0

        # Lặp từng channel và gửi từng request riêng
        for idx, ct in enumerate(channels, start=1):
            request_payload = {
                "stt": idx,
                "ma": ct["channel_code"],  # Mã danh mục
                "ten": ct["channel_name"],  # Tên danh mục
                "trang_thai": True
            }

            # Ghi log request từng channel
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi từng Channel
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/CustomerChannel",
                method="POST",
                body=request_payload
            )

            if response.get("status"):
                frappe.db.set_value("Channel", {"channel_code": ct["channel_code"]}, "is_sync", True)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync channel {ct['channel_code']}: {response}")

        frappe.db.commit()

        # Tổng kết kết quả
        message = f"Channel sync done. Success: {success_count}, Failed: {fail_count}"
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
            message="Exception occurred while syncing channel.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}