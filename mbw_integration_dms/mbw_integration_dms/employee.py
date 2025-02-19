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
        employee_list = kwargs.get("data", [])
        results = []  # Danh sách kết quả trả về

        for employee_data in employee_list:
            id_log_dms = employee_data.get("id_log", "")

            try:
                # Ghi log bắt đầu request
                create_dms_log(
                    status="Processing",
                    request_data=employee_data,
                    message="Starting Employee and Sales Person creation"
                )

                # Tạo Employee mới
                employee = frappe.get_doc({
                    "doctype": "Employee",
                    "first_name": validate_not_none(employee_data.get("employee_name"), "Employee Name"),
                    "date_of_birth": validate_date(float(employee_data.get("date_of_birth")) / 1000),
                    "gender": validate_not_none(employee_data.get("gender"), "Gender"),
                    "company_email": employee_data.get("email"),
                    "date_of_joining": nowdate(),
                    "status": "Active"
                })
                employee.insert(ignore_permissions=True)

                # Tạo Sales Person mới liên kết với Employee
                sales_person = frappe.get_doc({
                    "doctype": "Sales Person",
                    "sales_person_name": employee.employee_name,
                    "employee": employee.name,
                    "parent_sales_person": "",
                    "enabled": 1
                })
                sales_person.insert(ignore_permissions=True)

                # Ghi log thành công
                create_dms_log(
                    status="Success",
                    request_data=employee_data,
                    response_data={"employee_id": employee.name, "sales_person_id": sales_person.name},
                    message="Employee and Sales Person created successfully"
                )

                if id_log_dms:
                    create_partner_log(
                        id_log_dms=id_log_dms,
                        status=True,
                        title="Employee and Sales Person created successfully.",
                        message=f"Employee {employee.name} and Sale Person {sales_person.name} created successfully."
                    )

                results.append({
                    "status": "success",
                    "message": "Employee and Sales Person created successfully",
                    "employee_id": employee.name,
                    "sales_person_id": sales_person.name
                })

            except Exception as e:
                # Ghi log lỗi nếu có lỗi khi tạo Employee hoặc Sales Person
                create_dms_log(
                    status="Failed",
                    request_data=employee_data,
                    exception=e,
                    rollback=True,
                    message="Error occurred while creating Employee and Sales Person"
                )

                if id_log_dms:
                    create_partner_log(
                        id_log_dms=id_log_dms,
                        status=False,
                        title="Error occurred while creating Employee and Sales Person.",
                        message=str(e)
                    )

                results.append({
                    "status": "error",
                    "message": str(e),
                    "employee_data": employee_data
                })

        return results

    except Exception as e:
        frappe.throw(f"Lỗi xử lý danh sách nhân viên: {str(e)}")
