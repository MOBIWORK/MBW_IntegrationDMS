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

@frappe.whitelist()
def sync_provider_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Provider sync job started.")

        # Lấy danh sách nhà cung cấp chưa đồng bộ
        providers = frappe.get_all(
            "Supplier",
            filters={"is_sync": False},
            fields=["name", "supplier_name", "is_sync"]
        )

        if not providers:
            create_dms_log(status="Skipped", message="No new provider to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new provider to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo DMS API Client
        dms_client = DMSApiClient()

        total = len(providers)
        success_count = 0
        fail_count = 0

        for idx, ct in enumerate(providers, start=1):
            payload = {
                "stt": idx,
                "ma": ct["name"],               # Mã nhà cung cấp
                "ten": ct["supplier_name"],      # Tên nhà cung cấp
                "trang_thai": True                  # Trạng thái hoạt động
            }

            # Log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=payload
            )

            # Gửi dữ liệu đến API
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/ItemSupplier",
                method="POST",
                body=payload
            )

            # Xử lý phản hồi
            if success and response.get("status"):
                frappe.db.set_value("Supplier", ct["name"], "is_sync", True, update_modified=False)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync provider {ct['supplier_name']}: {response}")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync provider {ct['supplier_name']}."
                )

        frappe.db.commit()

        # Tổng kết
        summary_msg = f"Provider sync completed. Success: {success_count}/{total}, Failed: {fail_count}/{total}"
        create_dms_log(
            status="Success" if fail_count == 0 else "Partial Success",
            message=summary_msg
        )
        publish(KEY_REALTIME["key_realtime_categories"], summary_msg, done=True)

        return {"message": summary_msg}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing provider.",
            rollback=True
        )
        frappe.logger().error(f"Provider Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}

    
def update_status_after_change(doc, method):
    doc.is_sync = 0