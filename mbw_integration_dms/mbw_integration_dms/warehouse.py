# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

# Đồng bộ danh sách kho hàng
def sync_warehouse():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.warehouse.sync_warehouse_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Warehouse Sync job has been queued."}

def sync_warehouse_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Warehouse sync job started.")

        # Lấy danh sách warehouse chưa đồng bộ
        warehouses = frappe.get_all(
            "Warehouse",
            filters={"is_sync": False, "is_sale_dms": True, "disabled": False},
            fields=["warehouse_name", "name", "is_sync"]
        )

        if not warehouses:
            create_dms_log(status="Skipped", message="No new warehouse to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new warehouse to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        total = len(warehouses)
        success_count = 0
        fail_count = 0

        for idx, ct in enumerate(warehouses, start=1):
            single_payload = {
                "stt": idx,
                "ma": ct["name"],                 # Mã danh mục (name của Warehouse)
                "ten": ct["warehouse_name"],      # Tên danh mục (warehouse_name)
                "loai_kho": 0,                    # 0: Kho bán hàng (theo yêu cầu)
                "trang_thai": True
            }

            # Ghi log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=single_payload
            )

            # Gửi dữ liệu từng warehouse
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/Warehouse",
                method="POST",
                body=single_payload
            )

            # Nếu thành công, đánh dấu là đã sync
            if success and response.get("status"):
                frappe.db.set_value("Warehouse", ct["name"], "is_sync", True, update_modified=False)
                success_count += 1
            else:
                fail_count += 1
                frappe.logger().error(f"Failed to sync warehouse {ct['warehouse_name']}: {response}")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync warehouse {ct['warehouse_name']}."
                )

        frappe.db.commit()

        # Tổng kết kết quả
        summary_msg = f"Warehouse sync completed. Success: {success_count}/{total}, Failed: {fail_count}/{total}"
        create_dms_log(status="Success" if fail_count == 0 else "Partial Success", message=summary_msg)
        publish(KEY_REALTIME["key_realtime_categories"], summary_msg, done=True)

        return {"message": summary_msg}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing warehouse.",
            rollback=True
        )
        frappe.logger().error(f"Warehouse Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}

    
def update_status_after_change(doc, method):
    if doc.is_sale_dms == 1:
        doc.is_sync = 0