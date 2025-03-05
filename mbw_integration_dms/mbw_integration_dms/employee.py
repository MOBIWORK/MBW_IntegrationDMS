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
    validate_date,
    validate_choice
)
from mbw_integration_dms.mbw_integration_dms.helpers import configs

@frappe.whitelist()
def create_employee_and_sales_person(**kwargs):
    """API xử lý danh sách nhân viên và ghi log"""
    try:
        request_data = kwargs.get("data", {})
        employee_list = request_data.get("employees", [])  # Danh sách nhân viên
        id_log_dms = request_data.get("id_log", "")  # ID log chung
        results = []  # Danh sách kết quả trả về
        failed_records = []  # Danh sách lỗi

        # Ghi log bắt đầu request
        create_dms_log(
            status="Processing",
            request_data=kwargs,
            message="Starting Employee and Sales Person creation"
        )

        for employee_data in employee_list:
            email = employee_data.get("email")
            gender_data = employee_data.get("gender")
            emp_name = employee_data.get("employee_name")

            try:
                # Kiểm tra nếu Employee đã tồn tại theo company_email
                existing_employee = frappe.get_all("Employee", filters={"company_email": email}, fields=["name", "first_name"])

                if existing_employee:
                    # Nếu tồn tại, cập nhật Employee
                    employee = frappe.get_doc("Employee", existing_employee[0]["name"])
                    employee.first_name = validate_not_none(employee_data.get("employee_name"), "Employee Name")
                    employee.date_of_birth = validate_date(float(employee_data.get("date_of_birth")) / 1000)
                    employee.gender = validate_choice(configs.gender)(gender_data)
                    employee.status = "Active"
                    employee.save(ignore_permissions=True)
                    is_new = False
                    sales_person_name = None  # Không tạo mới Sales Person
                else:
                    # Nếu không tồn tại, tạo mới Employee
                    employee = frappe.get_doc({
                        "doctype": "Employee",
                        "first_name": validate_not_none(employee_data.get("employee_name")),
                        "date_of_birth": validate_date(float(employee_data.get("date_of_birth")) / 1000),
                        "gender": validate_choice(configs.gender)(gender_data),
                        "company_email": email,
                        "date_of_joining": nowdate(),
                        "status": "Active"
                    })
                    employee.insert(ignore_permissions=True)
                    is_new = True

                    # Kiểm tra xem đã có Sales Person trùng tên chưa
                    existing_sales_persons = frappe.get_all("Sales Person", filters={"sales_person_name": emp_name}, fields=["name"])
                    if existing_sales_persons:
                        sales_person_name = f"{emp_name}-{len(existing_sales_persons) + 1}"
                    else:
                        sales_person_name = emp_name

                    # Chỉ tạo mới Sales Person nếu Employee mới được tạo
                    sales_person = frappe.get_doc({
                        "doctype": "Sales Person",
                        "sales_person_name": emp_name,
                        "employee": employee.name,
                        "email": email,
                        "parent_sales_person": "",
                        "enabled": 1
                    })
                    sales_person.insert(ignore_permissions=True)

                results.append({
                    "status": "success",
                    "message": "Employee updated successfully" if not is_new else "Employee and Sales Person created successfully",
                    "employee_id": employee.name,
                    "sales_person_id": sales_person_name if is_new else None,
                    "is_new_employee": is_new
                })

            except Exception as e:
                failed_records.append({
                    "status": "error",
                    "message": str(e),
                    "employee_data": employee_data
                })

        # Ghi log kết thúc request (chỉ log thành công hoặc thất bại)
        if failed_records:
            create_dms_log(
                status="Failed",
                request_data=kwargs,
                response_data=failed_records,
                message="Some Employees failed to process"
            )

            failed_records_message = failed_records[0]["message"]
            if id_log_dms:
                create_partner_log(
                    id_log_dms=id_log_dms,
                    status=False,
                    title="Some Employee creations failed.",
                    message=f"Some Employees could not be processed: {failed_records_message}."
                )

            return failed_records

        else:
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
        # Ghi log thất bại toàn bộ request nếu có lỗi lớn
        create_dms_log(
            status="Error",
            request_data=kwargs,
            exception=e,
            rollback=True,
            message="Critical error occurred while processing Employee and Sales Person"
        )