# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách đơn vị tính
def sync_unit():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.unit.sync_unit_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Unit Sync job has been queued."}

def sync_unit_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Unit sync job started.")

        # Lấy danh sách unit chưa đồng bộ
        units = frappe.get_all(
            "UOM",
            filters={"is_sync": False},
            fields=["name", "uom_name", "enabled", "is_sync"]
        )

        if not units:
            create_dms_log(status="Skipped", message="No new unit to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new unit to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        total = len(units)
        success_count = 0
        fail_count = 0

        # Gửi từng đơn vị đo lường một
        for idx, ct in enumerate(units, start=1):
            single_payload = {
                "stt": idx,
                "ma": ct["name"],        # Mã danh mục (ví dụ: "Kg", "Cái")
                "ten": ct["uom_name"],   # Tên danh mục
                "trang_thai": bool(ct["enabled"])  # True/False
            }

            # Ghi log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=single_payload
            )

            # Gửi dữ liệu đến DMS
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/ItemUnit",
                method="POST",
                body=single_payload
            )

            # Xử lý kết quả
            if success and response.get("status"):
                frappe.db.set_value("UOM", ct["name"], "is_sync", True, update_modified=False)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync unit {ct['uom_name']}: {response}")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync unit {ct['uom_name']}."
                )

        frappe.db.commit()

        # Tổng kết kết quả
        summary_msg = f"Unit sync completed. Success: {success_count}/{total}, Failed: {fail_count}/{total}"
        create_dms_log(status="Success" if fail_count == 0 else "Partial Success", message=summary_msg)
        publish(KEY_REALTIME["key_realtime_categories"], summary_msg, done=True)

        return {"message": summary_msg}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing unit.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    

def update_status_after_change(doc, method):
    if doc.is_sale_dms == 1:
        doc.is_sync = 0