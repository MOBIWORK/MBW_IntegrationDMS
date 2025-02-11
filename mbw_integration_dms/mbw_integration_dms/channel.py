import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


# Đồng bộ danh sách kênh
def sync_channel():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.channel.sync_channel_job", queue="long", timeout=300)
    return {"message": "Channel Sync job has been queued."}

def sync_channel_job():
    try:
        create_dms_log(status="Queued", message="Channel sync job started.")

        # Lấy danh sách channel chưa đồng bộ
        channels = frappe.get_all(
            "Channel",
            filters={"is_sync": False},
            fields=["channel_name", "channel_code", "is_sync"]
        )

        if not channels:
            create_dms_log(status="Skipped", message="No new channel to sync.")
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["channel_code"],  # Mã danh mục
                "name": ct["channel_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in channels
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Channel",
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
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for ct in channels:
                frappe.db.set_value("Channel", {"channel_code": ct["channel_code"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Channel synced successfully."
            )
            return {"message": "Channel synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync channel."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing channel.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}