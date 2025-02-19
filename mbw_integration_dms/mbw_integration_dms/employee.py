# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe.utils import nowdate
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import (
    create_partner_log
)
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_not_none,
    validate_date
)

@frappe.whitelist()
def create_employee_and_sales_person(**kwargs):
    """API xử lý danh sách nhân viên và ghi log"""
    try:
        request_data = kwargs.get("data", {})
        employee_list = request_data.get("employees", [])  # Danh sách nhân viên
        id_log_dms = request_data.get("id_log", "")  # ID log
        results = []  # Danh sách kết quả trả về

        # Ghi log bắt đầu request
        create_dms_log(
            status="Processing",
            request_data=kwargs,
            message="Starting Employee and Sales Person creation"
        )

        for employee_data in employee_list:
            email = employee_data.get("email")

            try:
                # Kiểm tra nếu Employee đã tồn tại theo company_email
                existing_employee = frappe.get_all("Employee", filters={"company_email": email}, fields=["name", "first_name"])

                if existing_employee:
                    # Nếu tồn tại, cập nhật Employee
                    employee = frappe.get_doc("Employee", existing_employee[0]["name"])
                    employee.first_name = validate_not_none(employee_data.get("employee_name"), "Employee Name")
                    employee.date_of_birth = validate_date(float(employee_data.get("date_of_birth")) / 1000)
                    employee.gender = validate_not_none(employee_data.get("gender"), "Gender")
                    employee.status = "Active"
                    employee.save(ignore_permissions=True)
                    is_new = False

                    # Không tạo mới Sales Person nếu Employee đã tồn tại
                    sales_person_name = None
                else:
                    # Nếu không tồn tại, tạo mới Employee
                    employee = frappe.get_doc({
                        "doctype": "Employee",
                        "first_name": validate_not_none(employee_data.get("employee_name")),
                        "date_of_birth": validate_date(float(employee_data.get("date_of_birth")) / 1000),
                        "gender": validate_not_none(employee_data.get("gender")),
                        "company_email": email,
                        "date_of_joining": nowdate(),
                        "status": "Active"
                    })
                    employee.insert(ignore_permissions=True)
                    is_new = True

                    # Chỉ tạo mới Sales Person nếu Employee mới được tạo
                    sales_person = frappe.get_doc({
                        "doctype": "Sales Person",
                        "sales_person_name": employee.employee_name,
                        "employee": employee.name,
                        "parent_sales_person": "",
                        "enabled": 1
                    })
                    sales_person.insert(ignore_permissions=True)
                    sales_person_name = sales_person.name

                results.append({
                    "status": "success",
                    "message": "Employee updated successfully" if not is_new else "Employee and Sales Person created successfully",
                    "employee_id": employee.name,
                    "sales_person_id": sales_person_name if is_new else None,
                    "is_new_employee": is_new
                })

            except Exception as e:
                # Ghi log lỗi nếu có lỗi khi tạo hoặc cập nhật Employee
                create_dms_log(
                    status="Failed",
                    request_data=employee_data,
                    exception=e,
                    rollback=True,
                    message="Error occurred while processing Employee and Sales Person"
                )

                if id_log_dms:
                    create_partner_log(
                        id_log_dms=id_log_dms,
                        status=True,
                        title="Error occurred while processing Employee and Sales Person.",
                        message="Error occurred while processing Employee and Sales Person."
                    )

                results.append({
                    "status": "error",
                    "message": str(e),
                    "employee_data": employee_data
                })

        # Ghi log kết thúc request
        create_dms_log(
            status="Completed",
            request_data=kwargs,
            response_data=results,
            message="Finished processing Employee and Sales Person"
        )

        if id_log_dms:
            create_partner_log(
                id_log_dms=id_log_dms,
                status=True,
                title="Employee processing completed.",
                message="Employee creation and updates have been processed."
            )

        return results

    except Exception as e:
        frappe.throw(f"Lỗi xử lý danh sách nhân viên: {str(e)}")