# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from frappe.utils import getdate, today

enable_dms = check_enable_integration_dms()

@frappe.whitelist()
def get_timesheet_dms(**kwargs):
    if enable_dms:
        try:
            date = getdate(today())

            if kwargs.get("data"):
                data = kwargs.get("data")

                for record in data:
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
                                "tong_gio": round(timesheet_data.get("T", 0) / 60, 2),
                                "ve_som": round(timesheet_data.get("S", 0) / 60, 2),
                                "ve_muon": round(timesheet_data.get("M", 0) / 60, 2),
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
                            "naming_series": "TS-.MM.-.YYYY.-",
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
                    response_data=data,
                    message="Timesheet synced successfully."
                )
                return {
                    "success": True,
                    "message": "Timesheet synced successfully."
                }
            
            else:
                create_dms_log(
                    status="Failed",
                    response_data=data,
                    message="Failed to sync Timesheet DMS."
                )
                return {
                    "success": False,
                    "error": "Failed to sync Timesheet DMS. No data provided."
                    }

        except Exception as e:
            create_dms_log(
                status="Error",
                exception=str(e),
                message="Exception occurred while syncing Timesheet.",
                rollback=True
            )
            frappe.logger().error(f"Sync Error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
