# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe.utils import nowdate
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log

@frappe.whitelist()
def create_employee_and_sales_person(**kwargs):
    """
    API tạo hoặc cập nhật Employee và Sales Person theo payload DMS
    """
    try:
        payload = frappe._dict(kwargs)
        # data = payload.get("data", {}).get("data", [])
        data = payload.get("data", [])

        if not data:
            frappe.throw("Không có dữ liệu nhân viên để xử lý.")

        results, failed_records = [], []

        # --- Ghi log bắt đầu ---
        create_dms_log(
            status="Processing",
            request_data=payload,
            message=f"Bắt đầu xử lý {len(data)} nhân viên từ DMS"
        )

        for emp_data in data:
            emp = frappe._dict(emp_data)
            try:
                email = emp.get("email")
                full_name = emp.get("ten")
                gender = "Male" if emp.get("gioi_tinh") == "Nam" else "Female"
                phone = emp.get("so_dien_thoai")
                status = "Active" if emp.get("trang_thai") == "1" else "Left"

                if not email or not full_name:
                    raise ValueError("Thiếu email hoặc tên nhân viên")

                existing_emp = frappe.db.exists("Employee", {"company_email": email})

                if existing_emp:
                    # --- Cập nhật Employee ---
                    frappe.db.set_value("Employee", existing_emp, {
                        "gender": gender,
                        "status": status,
                        "cell_number": phone
                    })
                    is_new = False

                else:
                    # --- Tạo mới Employee ---
                    employee = frappe.new_doc("Employee")
                    employee.first_name = full_name
                    employee.gender = gender
                    employee.company_email = email
                    employee.cell_number = phone
                    employee.date_of_joining = nowdate()
                    employee.date_of_birth = "1999-01-01"
                    employee.status = status
                    employee.insert(ignore_permissions=True)
                    is_new = True

                # --- Có thể bật lại đoạn tạo Sales Person nếu cần ---
                sales_person_exists = frappe.db.exists("Sales Person", {"employee": employee.name})
                if not sales_person_exists:
                    sales_person = frappe.new_doc("Sales Person")
                    sales_person.sales_person_name = full_name
                    sales_person.employee = employee.name
                    sales_person.email = email
                    sales_person.enabled = 1
                    sales_person.insert(ignore_permissions=True)
                    sales_person_id = sales_person.name
                else:
                    sales_person_id = sales_person_exists

                results.append({
                    "status": "success",
                    "employee_id": employee.name,
                    "sales_person_id": sales_person_id,
                    "is_new_employee": is_new,
                    "email": email,
                    "message": "Đã cập nhật nhân viên" if not is_new else "Đã tạo mới nhân viên và Sales Person"
                })

            except Exception as e:
                frappe.db.rollback()
                failed_records.append({
                    "status": "error",
                    "message": str(e),
                    "employee_data": emp
                })
                frappe.log_error(frappe.get_traceback(), f"Employee Sync Error: {emp.get('ma')}")

        # --- Ghi log kết quả ---
        if failed_records:
            create_dms_log(
                status="Failed",
                request_data=payload,
                response_data={"success": results, "failed": failed_records},
                message=f"Có {len(failed_records)} nhân viên xử lý thất bại."
            )
            return {"status": False, "results": results, "failed": failed_records}

        else:
            create_dms_log(
                status="Completed",
                request_data=payload,
                response_data=results,
                message=f"Hoàn tất xử lý {len(results)} nhân viên từ DMS."
            )
            return {"status": True, "results": results, "total": len(results)}

    except Exception as e:
        frappe.db.rollback()
        create_dms_log(
            status="Error",
            request_data=kwargs,
            exception=e,
            rollback=True,
            message=f"Lỗi nghiêm trọng khi xử lý Employee DMS: {str(e)}"
        )
        frappe.throw(f"Lỗi xử lý Employee DMS: {str(e)}")