# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from frappe.utils import getdate, today, get_last_day, get_first_day
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

def get_timesheet_dms(**kwargs):
    try:
        dms_client = DMSApiClient()
        date = getdate(today())
        tu_ngay = get_first_day(date).strftime("%d/%m/%Y")
        den_ngay = get_last_day(date).strftime("%d/%m/%Y")

        # Dữ liệu gửi đi
        request_payload = {
            "orgid": dms_client.orgid,
            "tu_ngay": tu_ngay,
            "den_ngay": den_ngay
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            message="Sync Timesheets DMS",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/PublicAPI/Timesheets",
            method="POST",
            body=request_payload
        )

        if response.get("result"):
            results = response.get("result")

            for record in results:
                employee_code = record.get("code")
                employee_name = record.get("name")
                email = record.get("email")

                if not frappe.db.exists("Sales Person", {"name": employee_name}):
                    continue
                
                # Tạo danh sách dữ liệu chấm công theo ngày
                timesheet_details = []
                for day in range(1, 32):
                    if str(day) in record:
                        timesheet_data = record[str(day)]
                        timesheet_details.append({
                            "date": day,
                            "gio_vao": timesheet_data.get("V", ""),
                            "gio_ra": timesheet_data.get("R", ""),
                            "tong_gio": timesheet_data.get("T", 0),
                            "ve_som": timesheet_data.get("S", 0),
                            "ve_muon": timesheet_data.get("M", 0),
                            "cong": timesheet_data.get("NC", 0),
                            "dia_chi_vao": timesheet_data.get("addV", ""),
                            "dia_chi_ra": timesheet_data.get("addR", ""),
                        })

                # Kiểm tra bản ghi đã tồn tại chưa
                existing_kpi = frappe.db.exists(
                    "DMS Timesheets", 
                    {
                        "employee": employee_name,
                        "month": date.month,
                        "year": date.year
                    }
                )

                if existing_kpi:
                    # Nếu đã tồn tại, lấy bản ghi hiện có
                    timesheet_doc = frappe.get_doc("DMS Timesheets", existing_kpi)

                    # Xóa dữ liệu cũ của bảng con
                    timesheet_doc.set("timesheets_detail", [])

                    # Thêm dữ liệu mới vào bảng con
                    for detail in timesheet_details:
                        timesheet_doc.append("timesheets_detail", detail)

                    # Cập nhật thông tin tổng
                    timesheet_doc.update({
                        "total_days": record.get("Totalday", 0),
                        "total_ls": record.get("totalS", 0),
                        "total_lm": record.get("totalM", 0),
                        "total_t": record.get("totalT", 0),
                        "total_nc": record.get("totalNC", 0),
                    })

                    # Lưu bản ghi
                    timesheet_doc.save(ignore_permissions=True)

                else:
                    # Nếu chưa tồn tại, tạo mới bản ghi
                    new_kpi = frappe.get_doc({
                        "doctype": "DMS Timesheets",
                        "employee_code": employee_code,
                        "employee": employee_name,
                        "email": email,
                        "month": date.month,
                        "year": date.year,
                        "total_days": record.get("Totalday", 0),
                        "total_ls": record.get("totalS", 0),
                        "total_lm": record.get("totalM", 0),
                        "total_t": record.get("totalT", 0),
                        "total_nc": record.get("totalNC", 0),
                        "timesheets_detail": []
                    })

                    # Thêm dữ liệu vào bảng con
                    for detail in timesheet_details:
                        new_kpi.append("timesheets_detail", detail)

                    # Lưu bản ghi mới
                    new_kpi.insert(ignore_permissions=True)

            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Timesheet synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_timesheet"], "Timesheet synced successfully.", done=True)
            return {"message": "Timesheet synced successfully."}
        
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync Timesheet DMS."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_timesheet"], f"Failed to sync: {response}", error=True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing Timesheet.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}
