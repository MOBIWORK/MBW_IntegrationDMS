# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
import pydash
import json

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms

from mbw_integration_dms.mbw_integration_dms.helpers import configs
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import (
    create_address_customer,
    create_partner_log,
    publish
)
from mbw_integration_dms.mbw_integration_dms.helpers.validators import (
    validate_date, 
    validate_phone_number, 
    validate_choice,
    validate_not_none,
)

from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

def sync_customer():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_customer"])
        return {"message": "Customer Sync job has been queued."}

def sync_customer_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer sync job started.")

        # Lấy danh sách Customer chưa đồng bộ
        customers = frappe.get_all(
            "Customer",
            filters={"is_sync": False, "is_sales_dms": True},
            fields=["customer_code_dms", "customer_name", "is_sales_dms", "email_id", "mobile_no", "tax_id", "dms_customer_group",
                    "dms_customer_type", "sfa_sale_channel", "territory", "customer_primary_contact", "customer_primary_address", "primary_address"]
        )

        if not customers:
            create_dms_log(status="Skipped", message="No new customer to sync.")
            publish(KEY_REALTIME["key_realtime_customer"], "No new customer to sync.", done = True)
            return {"message": "No new data to sync."}
        
        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = []
        for i in customers:
            longitude = None
            latitude = None
            address = None
            address_shipping = None
            phone_number = None

            if i.get("customer_primary_address"):
                addresses = frappe.get_all(
                    "Address",
                    filters={"name": i["customer_primary_address"]},
                    fields=["address_title", "address_location"]
                )
            
                for address_entry in addresses:
                    # Lấy địa chỉ chính (primary address)
                    address = address_entry.address_title
                    address_shipping = address_entry.address_title

                    # Lấy tọa độ từ address_location
                    if address_entry.get("address_location"):
                        try:
                            location_data = json.loads(address_entry.address_location)
                            longitude = location_data.get("long")
                            latitude = location_data.get("lat")
                        except Exception as e:
                            frappe.log_error(f"JSON parsing error for address {address_entry.name}: {str(e)}")

            if i.get("customer_primary_contact"):
                contact_info = frappe.get_doc("Contact", i["customer_primary_contact"])

                # Lấy tất cả các số điện thoại liên kết
                if contact_info and contact_info.phone_nos:
                    # Chỉ lấy số điện thoại đầu tiên, bạn có thể điều chỉnh nếu muốn lấy tất cả
                    phone_number = contact_info.phone_nos[0].phone if contact_info.phone_nos else ""

            formatted_data.append({
                "code": i["customer_code_dms"],
                "name": i["customer_name"],
                "trang_thai": True,
                "email": i["email_id"],
                "mst": i["tax_id"],
                "nhom_khach_hang": i["dms_customer_group"],
                "loai_khach_hang": i["dms_customer_type"],
                "kenh": i["sfa_sale_channel"],
                "khu_vuc": i["territory"],
                "sdt": i["mobile_no"] if i["mobile_no"] else phone_number,
                "nguoi_lien_he": i["customer_primary_contact"],
                "address": address if address else "",
                "address_shipping": address_shipping if address_shipping else "",
                "long": longitude,
                "lat": latitude
            })

        # Dữ liệu gửi đi
        request_payload = {
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
            endpoint="/PublicAPI/CustomerSync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for i in customers:
                frappe.db.set_value("Customer", {"customer_code_dms": i["customer_code_dms"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Customers synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_customer"], "Customers synced successfully.", done = True)
            return {"message": "Customers synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync customers."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_customer"], f"Failed to sync: {response}", error = True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer.",
            rollback=True
        )
        publish(KEY_REALTIME["key_realtime_customer"], f"Sync Error: {str(e)}", error = True)
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}
    

# Đồng bộ danh sách loại khách hàng
def sync_customer_type():
    """ Đưa job vào hàng đợi để đồng bộ Customer Type """
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_type_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Customer Type Sync job has been queued."}

def sync_customer_type_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer Type sync job started.")

        # Lấy danh sách Customer Type chưa đồng bộ
        customer_types = frappe.get_all(
            "Customer Type",
            filters={"is_sync": False},
            fields=["customer_type_id", "customer_type_name", "is_sync"]
        )

        if not customer_types:
            create_dms_log(status="Skipped", message="No new customer types to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], f"No new customer types to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["customer_type_id"],  # Mã danh mục
                "name": ct["customer_type_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in customer_types
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "CustomerType",
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
            endpoint="/PublicAPI/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for ct in customer_types:
                frappe.db.set_value("Customer Type", {"customer_type_id": ct["customer_type_id"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Customer Types synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], f"Customer Types synced successfully.", done = True)
            return {"message": "Customer Types synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync customer types."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], f"Failed to sync: {response}", error = True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer types.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error = True)
        return {"error": str(e)}
    
# Đồng bộ danh sách nhóm khách hàng
def sync_customer_group():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_group_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Customer Group Sync job has been queued."}

def sync_customer_group_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer Type sync job started.")

        # Lấy danh sách Customer Group chưa đồng bộ
        customer_groups = frappe.get_all(
            "DMS Customer Group",
            filters={"is_sync": False},
            fields=["customer_group", "name_customer_group", "is_sync"]
        )

        if not customer_groups:
            create_dms_log(status="Skipped", message="No new customer group to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], f"No new customer group to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["customer_group"],  # Mã danh mục
                "name": ct["name_customer_group"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in customer_groups
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "CustomerGroup",
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
            endpoint="/PublicAPI/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if response.get("status"):
            for ct in customer_groups:
                frappe.db.set_value("DMS Customer Group", {"customer_group": ct["customer_group"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Customer Group synced successfully."
            )
            publish(KEY_REALTIME["key_realtime_categories"], f"Customer Group synced successfully.", done = True)
            return {"message": "Customer Group synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync customer group."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_categories"], f"Failed to sync: {response}", error = True)
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer groups.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error = True)
        return {"error": str(e)}
    

# Thêm mới khách hàng
@frappe.whitelist(methods="POST")
def create_customers(**kwargs):
    results = []
    try:
        data = kwargs.get("data", {})
        customer_list = data.get("customers", [])  # Danh sách nhân viên
        id_log_dms = data.get("id_log", "")  # ID log chung

        for customer_data in customer_list:
            try:
                customer_data = frappe._dict(customer_data)
                customer_code_dms = customer_data.get("customer_code_dms")

                # Kiểm tra nếu khách hàng đã tồn tại theo customer_code_dms
                existing_customer = frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms})

                if existing_customer:
                    # Nếu tồn tại, gọi hàm update_customer thay vì bỏ qua
                    update_result = update_customer(**customer_data)

                    create_dms_log(
                        status="Updated",
                        request_data=data,
                        response_data=update_result,
                        message=f"Customer {customer_code_dms} updated successfully."
                    )
                    
                    if id_log_dms:
                        create_partner_log(
                            id_log_dms=id_log_dms,
                            status=True,
                            title="Customer updated successfully.",
                            message=f"Customer {customer_code_dms} updated successfully."
                        )

                    results.append({"customer_code_dms": customer_code_dms, "status": "Updated"})
                    continue  # Tiếp tục với khách hàng khác

                # Nếu không tồn tại, tiến hành tạo mới khách hàng
                phone_number = ""
                address = customer_data.get("address")
                contact = customer_data.get("contact")

                if contact and contact.get("phone_number"):
                    phone_number = validate_phone_number(contact.get("phone_number"))

                # Ghi log bắt đầu tạo khách hàng
                create_dms_log(
                    status="Processing",
                    method="POST",
                    request_data=data,
                    message=f"Creating customer {customer_data.get('customer_name')}"
                )

                # Tạo mới khách hàng
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
                        if key == "territory" and isinstance(value, str):
                            territory = value.strip().split(",")[-1].strip()
                            new_customer.set(key, territory)
                        else:
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

                sales_person = None
                user_mail = customer_data.get("nhan_vien_pt")
                sales_person_name = frappe.get_value("Sales Person", {"email": user_mail}, "name")
                if sales_person_name:
                    sales_person = sales_person_name
                else:
                    employee = frappe.get_value("Employee", {"user_id": user_mail}, "name")
                    sales_person = frappe.get_value("Sales Person", {"employee": employee}, "name")

                new_customer.append("sales_team", {
                    "sales_person": sales_person,
                    "allocated_percentage": 100,
                })
                new_customer.insert()

                # Xử lý địa chỉ khách hàng
                address = frappe._dict(address) if address else None
                current_address = None
                if address and address.address_title:
                    current_address = create_address_customer(address, {})

                # Xử lý contact khách hàng
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

                # Liên kết địa chỉ với khách hàng
                if current_address:
                    link_cs_address = {"link_doctype": new_customer.doctype, "link_name": new_customer.name}
                    current_address.append("links", link_cs_address)
                    current_address.save()

                    new_customer.customer_primary_address = current_address.name if frappe.db.exists("Address", current_address.name) else current_address.address_title
                    new_customer.primary_address = current_address.address_title
                    new_customer.save()

                # Liên kết contact với khách hàng
                if new_contact:
                    link_cs_contact = {"link_doctype": new_customer.doctype, "link_name": new_customer.name}
                    new_contact.append("links", link_cs_contact)
                    new_contact.save()
                    new_customer.customer_primary_contact = new_contact.name
                    new_customer.save()

                frappe.db.commit()

                # Ghi log thành công
                create_dms_log(
                    status="Success",
                    response_data={"customer": new_customer.name},
                    message=f"Customer {new_customer.name} created successfully."
                )
                
                if id_log_dms:
                    create_partner_log(
                        id_log_dms=id_log_dms,
                        status=True,
                        title="Customer create successfully.",
                        message=f"Customer {customer_code_dms} create successfully."
                    )
                
                results.append({"customer_code_dms": customer_data.get("customer_code_dms"), "status": "Success"})

            except Exception as e:
                error_message = f"Error creating/updating customer {customer_data.get('customer_code_dms')}: {str(e)}"

                # Ghi log thất bại
                create_dms_log(
                    status="Failed",
                    request_data=data,
                    message=error_message
                )
                
                if id_log_dms:
                    create_partner_log(
                        id_log_dms=id_log_dms,
                        status=False,
                        title="Customer create failed.",
                        message=error_message
                    )

                # Xóa bản ghi nếu đã tạo trước đó
                try:
                    if "new_customer" in locals() and new_customer:
                        frappe.delete_doc("Customer", new_customer.name, ignore_permissions=True)

                    if "current_address" in locals() and current_address:
                        frappe.delete_doc("Address", {"address_title": ["like", f"%{current_address.address_title}%"]}, ignore_permissions=True)

                    if "new_contact" in locals() and new_contact:
                        frappe.delete_doc("Contact", new_contact.name, ignore_permissions=True)

                except Exception as cleanup_error:
                    frappe.logger().error(f"Cleanup failed: {str(cleanup_error)}")

                results.append({"customer_code_dms": customer_data.get("customer_code_dms"), "status": "Failed", "error": str(e)})

        return {"results": results}

    except Exception as e:
        frappe.throw(f"Lỗi xử lý danh sách khách hàng: {str(e)}")

    
# Chỉnh sửa khách hàng
@frappe.whitelist(methods="PUT")
def update_customer(**kwargs):
    try:
        customer_code_dms = kwargs.get("customer_code_dms")

        # Ghi log khi API bắt đầu chạy
        create_dms_log(
            status="Processing",
            method="PUT",
            request_data=kwargs,
            message=f"Đang cập nhật khách hàng: {customer_code_dms}"
        )

        if not frappe.db.exists("Customer", {"customer_code_dms": customer_code_dms}, cache=True):
            frappe.throw(f"Không tồn tại khách hàng {customer_code_dms}")

        customer = frappe.get_doc("Customer", {"customer_code_dms": customer_code_dms})

        # Cập nhật các trường cơ bản của khách hàng
        fields = [
            "customer_name", "dms_customer_group", "territory",
            "website", "customer_type", "dms_customer_type", "sfa_sale_channel",
            "customer_code_dms", "tax_id", "email_id", "mobile_no"
        ]
        date_fields = ["custom_birthday"]

        for key, value in kwargs.items():
            if key in fields:
                if key == "territory" and isinstance(value, str):
                    territory = value.strip().split(",")[-1].strip()
                    customer.set(key, territory)
                else:
                    customer.set(key, value)
            elif key in date_fields and value is not None:
                customer.set(key, validate_date(float(value)/1000))

        # Cập nhật hoặc thêm mới địa chỉ
        if kwargs.get("address"):
            update_customer_addresses(customer, kwargs.get("address"), customer.name)

        # Cập nhật hoặc thêm mới liên hệ
        if kwargs.get("contacts"):
            update_customer_contacts(customer, kwargs.get("contacts"), customer.name)

        customer.save()

        # Ghi log thành công
        create_dms_log(
            status="Success",
            response_data={"message": "Cập nhật thông tin khách hàng thành công"},
            message=f"Khách hàng {customer.name} đã được cập nhật thành công"
        )

        return "Cập nhật thông tin khách hàng thành công"

    except Exception as e:
        # Ghi log khi gặp lỗi
        create_dms_log(
            status="Error",
            request_data=kwargs,
            message=f"Lỗi khi cập nhật khách hàng {customer_code_dms}: {str(e)}"
        )
        frappe.throw(f"Lỗi cập nhật khách hàng {customer_code_dms}: {str(e)}")

# Cập nhật địa chỉ khách hàng
def update_customer_addresses(customer, addresses, customer_name):
    link_cs_address = {"link_doctype": "Customer", "link_name": customer_name}
    create_address_customer(addresses, link_cs_address)

    primary_address = pydash.find(addresses, lambda x: isinstance(x, dict) and x.get("primary") == 1)
    if primary_address:
        set_primary_address(customer, primary_address)

def set_primary_address(customer, address_data):
    address_id = address_data.get("name") or frappe.get_value(
        "Address", {"address_title": ["like", f"%{address_data['address_title']}%"]}, "name"
    )
    if address_id:
        customer.customer_primary_address = address_id
        customer.save()

# Cập nhật liên hệ khách hàng
def update_customer_contacts(customer, contacts, customer_name):
    for contact_data in contacts:
        contact = frappe.get_doc("Contact", contact_data.get("name")) if frappe.db.exists("Contact", contact_data.get("name")) else None
        if contact:
            unlink_and_delete_contact(contact, customer_name)

        new_contact = create_new_contact(contact_data, customer_name)
        
        if new_contact and pydash.find(contacts, lambda x: x.get("primary") == 1):
            customer.customer_primary_contact = new_contact.name
            customer.save()

def unlink_and_delete_contact(contact, customer_name):
    frappe.db.sql("""
        UPDATE `tabCustomer`
        SET customer_primary_contact=NULL, mobile_no=NULL, email_id=NULL
        WHERE name=%s AND customer_primary_contact=%s
    """, (customer_name, contact.name))

    if contact.address:
        frappe.db.delete("Address", contact.address)
    if contact.name:
        frappe.db.delete("Contact", contact.name)

# Tạo mới liên hệ khách hàng
def create_new_contact(contact_data, customer_name, address_data):
    new_contact = frappe.new_doc("Contact")
    new_contact.update({
        "first_name": contact_data.get("first_name"),
        "last_name": contact_data.get("last_name"),
        "is_primary_contact": contact_data.get("is_primary_contact", 0),
        "is_billing_contact": contact_data.get("is_billing_contact", 0)
    })
    
    if contact_data.get("phone"):
        new_contact.append("phone_nos", {"phone": contact_data["phone"], "is_primary_mobile_no": 1})

    new_contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})
    new_contact.insert()

    return new_contact


# Xóa khách hàng
def delete_customer(doc, method):
    dms_client = DMSApiClient()
    customer_codes = [doc.customer_code_dms] if isinstance(doc, frappe.model.document.Document) else doc

    request_payload = {
        "orgid": dms_client.orgid,
        "data": customer_codes
    }

    # Ghi log request
    create_dms_log(
        status="Processing",
        method="POST",
        request_data=request_payload,
        message=f"Sending delete request for customers: {', '.join(customer_codes)}"
    )

    try:
        # Gửi request xóa kh đến API DMS
        response, success = dms_client.request(
            endpoint="/PublicAPI/CustomerDel",
            method="POST",
            body=request_payload
        )

        # Nếu API đối tác trả về lỗi, không xóa kh bên ERPNext
        if not success or not response.get("status"):
            frappe.throw(f"Không thể xóa khách hàng bên DMS: {response.get('message', 'Lỗi không xác định')}")

        # Nếu thành công, xóa khách hàng trong ERPNext
        frappe.db.sql("DELETE FROM `tabCustomer` WHERE customer_code_dms IN %s", (customer_codes,))
        frappe.db.commit()

        # Ghi log thành công
        create_dms_log(
            status="Success",
            response_data=response,
            message=f"Customers deleted successfully from both ERPNext and DMS: {', '.join(customer_codes)}"
        )

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Lỗi khi xóa khách hàng: {str(e)}", "Customer Deletion")
        frappe.throw(f"Lỗi khi xóa khách hàng: {str(e)}")


def update_status_after_change(doc, method):
    if doc.is_sales_dms == 1:
        doc.is_sync = 0