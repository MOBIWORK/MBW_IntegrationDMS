import frappe
import pydash

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log

from mbw_integration_dms.mbw_integration_dms.helpers import configs
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import create_address_customer
from mbw_integration_dms.mbw_integration_dms.customer import update_customer_addresses, update_customer_contacts
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_date, 
    validate_phone_number, 
    validate_choice,
    validate_not_none,
)

# Thêm mới khách hàng
@frappe.whitelist(methods="POST")
def create_customers_n8n(**kwargs):
    results = []
    try:
        data = kwargs
        customer_list = data.get("customers", [])
        id_log_dms = data.get("id_log", "")

        for customer_data in customer_list:
            try:
                customer_data = frappe._dict(customer_data)
                customer_code_dms = customer_data.get("customer_code_dms")

                existing_customer = frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms})

                if existing_customer:
                    update_result = update_customer_n8n(**customer_data)

                    create_dms_log(
                        status="Updated",
                        request_data=data,
                        response_data=update_result,
                        message=f"Customer {customer_code_dms} updated successfully."
                    )

                    results.append({
                        "customer_code_dms": customer_code_dms,
                        "status": "Updated",
                        "id_log_dms": id_log_dms
                    })
                    continue

                phone_number = ""
                address = customer_data.get("address")
                contact = customer_data.get("contact")

                if contact and contact.get("phone_number"):
                    phone_number = validate_phone_number(contact.get("phone_number"))

                create_dms_log(
                    status="Processing",
                    method="POST",
                    request_data=data,
                    message=f"Creating customer {customer_data.get('customer_name')}"
                )

                new_customer = frappe.new_doc("Customer")
                required_fields = ["customer_name", "customer_code_dms"]
                normal_fields = [
                    "customer_details", "website", "dms_customer_group", "territory", 
                    "dms_customer_type", "sfa_sale_channel", "mobile_no", "tax_id", 
                    "email_id", "is_sales_dms"
                ]
                choice_fields = ["customer_type"]
                date_fields = ["custom_birthday"]

                for key, value in customer_data.items():
                    if key in normal_fields:
                        new_customer.set(key, value)
                    elif key in required_fields:
                        required = validate_not_none(value)
                        new_customer.set(key, required)
                    elif key in date_fields:
                        custom_birthday = validate_date(float(value) / 1000) if value is not None else None
                        new_customer.set(key, custom_birthday)
                    elif key in choice_fields:
                        customer_type = validate_choice(configs.customer_type)(value)
                        new_customer.set(key, customer_type)

                new_customer.is_sync = 1
                new_customer.insert()

                address = frappe._dict(address) if address else None
                current_address = None
                if address and address.address_title:
                    current_address = create_address_customer(address, {})

                new_contact = None
                if contact and contact.get("first_name"):
                    new_contact = frappe.new_doc("Contact")
                    contact_fields = "first_name"
                    for key, value in contact.items():
                        if key in contact_fields:
                            new_contact.set(key, value)

                    new_contact.is_primary_contact = 1
                    new_contact.is_billing_contact = 1

                    if phone_number:
                        new_contact.append("phone_nos", {
                            "phone": phone_number,
                            "is_primary_phone": 1,
                            "is_primary_mobile_no": 1
                        })
                    new_contact.insert()

                if current_address:
                    link_cs_address = {"link_doctype": new_customer.doctype, "link_name": new_customer.name}
                    current_address.append("links", link_cs_address)
                    current_address.save()

                    new_customer.customer_primary_address = current_address.name if frappe.db.exists("Address", current_address.name) else current_address.address_title
                    new_customer.primary_address = current_address.address_title
                    new_customer.save()

                if new_contact:
                    link_cs_contact = {"link_doctype": new_customer.doctype, "link_name": new_customer.name}
                    new_contact.append("links", link_cs_contact)
                    new_contact.save()
                    new_customer.customer_primary_contact = new_contact.name
                    new_customer.save()

                frappe.db.commit()

                create_dms_log(
                    status="Success",
                    response_data={"customer": new_customer.name},
                    message=f"Customer {new_customer.name} created successfully."
                )
                
                results.append({
                    "customer_code_dms": customer_data.get("customer_code_dms"),
                    "status": "Success",
                    "id_log_dms": id_log_dms
                })

            except Exception as e:
                error_message = f"Error creating/updating customer {customer_data.get('customer_code_dms')}: {str(e)}"

                create_dms_log(
                    status="Failed",
                    request_data=data,
                    message=error_message
                )
                
                try:
                    if "new_customer" in locals() and new_customer:
                        frappe.delete_doc("Customer", new_customer.name, ignore_permissions=True)
                    if "current_address" in locals() and current_address:
                        frappe.delete_doc("Address", {"address_title": ["like", f"%{current_address.address_title}%"]}, ignore_permissions=True)
                    if "new_contact" in locals() and new_contact:
                        frappe.delete_doc("Contact", new_contact.name, ignore_permissions=True)
                except Exception as cleanup_error:
                    frappe.logger().error(f"Cleanup failed: {str(cleanup_error)}")

                results.append({
                    "customer_code_dms": customer_data.get("customer_code_dms"),
                    "status": "Failed",
                    "error": str(e),
                    "id_log_dms": id_log_dms
                })

        return {
            "success": True,
            "message": "Xử lý danh sách khách hàng thành công",
            "data": results
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Lỗi xử lý danh sách khách hàng: {str(e)}",
            "data": []
        }


# Chỉnh sửa khách hàng
@frappe.whitelist(methods="PUT")
def update_customer_n8n(**kwargs):
    try:
        customer_code_dms = kwargs.get("customer_code_dms")
        id_log_dms = kwargs.get("id_log", "")

        create_dms_log(
            status="Processing",
            method="PUT",
            request_data=kwargs,
            message=f"Đang cập nhật khách hàng: {customer_code_dms}"
        )

        if not frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms}, cache=True):
            return {
                "success": False,
                "message": f"Không tồn tại khách hàng {customer_code_dms}",
                "id_log_dms": id_log_dms
            }

        customer = frappe.get_doc("Customer", {"customer_code_dms": customer_code_dms})

        fields = [
            "customer_name", "dms_customer_group", "territory",
            "website", "customer_type", "dms_customer_type", "sfa_sale_channel",
            "customer_code_dms", "tax_id", "email_id", "mobile_no"
        ]
        date_fields = ["custom_birthday"]

        for key, value in kwargs.items():
            if key in fields:
                customer.set(key, value)
            elif key in date_fields and value is not None:
                customer.set(key, validate_date(float(value)/1000))

        if kwargs.get("address"):
            update_customer_addresses(customer, kwargs.get("address"), customer.name)

        if kwargs.get("contacts"):
            update_customer_contacts(customer, kwargs.get("contacts"), customer.name)

        customer.save()

        create_dms_log(
            status="Success",
            response_data={"message": "Cập nhật thông tin khách hàng thành công"},
            message=f"Khách hàng {customer.name} đã được cập nhật thành công"
        )

        return {
            "success": True,
            "message": f"Khách hàng {customer.name} đã được cập nhật thành công",
            "data": {
                "customer_name": customer.name,
                "customer_code_dms": customer.customer_code_dms
            },
            "id_log_dms": id_log_dms
        }

    except Exception as e:
        create_dms_log(
            status="Error",
            request_data=kwargs,
            message=f"Lỗi khi cập nhật khách hàng {customer_code_dms}: {str(e)}"
        )
        return {
            "success": False,
            "message": f"Lỗi cập nhật khách hàng {customer_code_dms}: {str(e)}",
            "id_log_dms": id_log_dms
        }