# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


# Đồng bộ danh sách đơn vị tính
def sync_unit():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.unit.sync_unit_job", queue="long", timeout=300)
    return {"message": "Unit Sync job has been queued."}

def sync_unit_job():
    try:
        create_dms_log(status="Queued", message="unit sync job started.")

        # Lấy danh sách unit chưa đồng bộ
        units = frappe.get_all(
            "UOM",
            filters={"is_sync": False},
            fields=["name", "uom_name", "enabled", "is_sync"]
        )

        if not units:
            create_dms_log(status="Skipped", message="No new unit to sync.")
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["name"],  # Mã danh mục
                "name": ct["unit_name"],  # Tên danh mục
                "isActive": ct["enabled"]  # Trạng thái danh mục
            }
            for ct in units
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "Unit",
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
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for ct in units:
                frappe.db.set_value("UOM", {"name": ct["name"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Unit synced successfully."
            )
            return {"message": "Unit synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync unit."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing unit.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}