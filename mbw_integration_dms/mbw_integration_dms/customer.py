# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from frappe import _
import pydash, json, datetime

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import (
    create_address_customer,
    publish
)
from mbw_integration_dms.mbw_integration_dms.helpers.validators import validate_date
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME

enable_dms = check_enable_integration_dms()

def sync_customer():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_customer"])
        return {"message": "Customer Sync job has been queued."}

@frappe.whitelist()
def sync_customer_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer sync job started.")

        # Lấy danh sách Customer chưa đồng bộ
        customers = frappe.get_all(
            "Customer",
            filters={"is_sync": False, "is_sales_dms": True},
            fields=[
                "name",
                "customer_code_dms",
                "customer_name",
                "email_id",
                "mobile_no",
                "tax_id",
                "dms_customer_group",
                "dms_customer_type",
                "sfa_sale_channel",
                "territory",
                "customer_primary_contact",
                "customer_primary_address",
            ]
        )

        if not customers:
            create_dms_log(status="Skipped", message="No new customer to sync.")
            publish(KEY_REALTIME["key_realtime_customer"], "No new customer to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo DMS API client
        dms_client = DMSApiClient()

        success_count = 0
        fail_count = 0

        # Lặp qua từng customer để gửi riêng lẻ
        for idx, i in enumerate(customers, start=1):
            address = ""
            address_shipping = ""
            phone_number = ""

            # Lấy địa chỉ chính
            if i.get("customer_primary_address"):
                address_doc = frappe.db.get_value(
                    "Address",
                    i["customer_primary_address"],
                    "address_title"
                )
                if address_doc:
                    address = address_doc
                    address_shipping = address_doc

            # Lấy số điện thoại liên hệ chính
            if i.get("customer_primary_contact"):
                contact_info = frappe.get_doc("Contact", i["customer_primary_contact"])
                if contact_info and contact_info.phone_nos:
                    phone_number = contact_info.phone_nos[0].phone

            # Chuẩn bị payload
            request_payload = {
                "ma_kh": i.get("customer_code_dms") or "",
                "ten_kh": i.get("customer_name") or "",
                "trang_thai": True,
                "trang_thai_kh": "Hoạt động",
                "email": i.get("email_id") or "",
                "nhom_kh": i.get("dms_customer_group") or "",
                "loai_kh": i.get("dms_customer_type") or "",
                "kenh": i.get("sfa_sale_channel") or "",
                "khu_vuc": i.get("territory") or "",
                "sdt": i.get("mobile_no") or phone_number or "",
                "nguoi_lien_he": i.get("customer_primary_contact") or "",
                "dia_chi": address,
                "dia_chi_gh": address_shipping,
                "hinh_anh": "",
                "han_muc_cn": "",
            }

            # Ghi log từng bản ghi
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi request từng Customer
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/Customer",
                method="POST",
                body=request_payload
            )

            # Nếu thành công
            if response.get("status"):
                frappe.db.set_value("Customer", i["name"], "is_sync", True)
                success_count += 1

                create_dms_log(
                    status="Success",
                    response_data=response,
                    message=f"Customer {i['customer_name']} synced successfully."
                )
                publish(
                    KEY_REALTIME["key_realtime_customer"],
                    f"Synced Customer {i['customer_name']} successfully.",
                )

            else:
                fail_count += 1
                error_message = response.get("message", "Failed to sync.")
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync Customer {i['customer_name']}: {error_message}"
                )
                frappe.logger().error(f"Failed to sync Customer {i['name']}: {response}")
                publish(
                    KEY_REALTIME["key_realtime_customer"],
                    f"Failed to sync Customer {i['customer_name']}.",
                    error=True,
                )

        frappe.db.commit()

        # Tổng kết
        message = f"Customer sync completed. Success: {success_count}, Failed: {fail_count}"
        status = "Success" if fail_count == 0 else "Partial Success"

        create_dms_log(status=status, message=message)
        publish(KEY_REALTIME["key_realtime_customer"], message, done=True)

        return {"message": message}

    except Exception as e:
        frappe.db.rollback()
        err_msg = f"Exception occurred while syncing customers: {str(e)}"
        create_dms_log(
            status="Error",
            exception=str(e),
            message=err_msg,
            rollback=True
        )
        frappe.logger().error(f"[DMS Sync Exception] {err_msg}")
        publish(KEY_REALTIME["key_realtime_customer"], err_msg, error=True)
        return {"error": str(e)}
    

# Đồng bộ danh sách loại khách hàng
def sync_customer_type():
    """ Đưa job vào hàng đợi để đồng bộ Customer Type """
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_type_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Customer Type Sync job has been queued."}

@frappe.whitelist()
def sync_customer_type_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer Type sync job started.")

        # Lấy danh sách Customer Type chưa đồng bộ
        customer_types = frappe.get_all(
            "Customer Type",
            filters={"is_sync": False},
            fields=["name", "customer_type_id", "customer_type_name"]
        )

        if not customer_types:
            create_dms_log(status="Skipped", message="No new customer types to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new customer types to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        success_count = 0
        fail_count = 0

        for idx, ct in enumerate(customer_types, start=1):
            # Chuẩn bị payload cho từng bản ghi
            request_payload = {
                "stt": idx,
                "ma": ct.get("customer_type_id") or "",
                "ten": ct.get("customer_type_name") or "",
                "trang_thai": True
            }

            # Ghi log request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi từng Customer Type
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/CustomerType",
                method="POST",
                body=request_payload
            )

            # Xử lý kết quả từng bản ghi
            if response.get("status"):
                frappe.db.set_value("Customer Type", ct["name"], "is_sync", True)
                success_count += 1

                create_dms_log(
                    status="Success",
                    response_data=response,
                    message=f"Customer Type {ct['customer_type_name']} synced successfully."
                )

                publish(
                    KEY_REALTIME["key_realtime_categories"],
                    f"Synced Customer Type {ct['customer_type_name']} successfully.",
                )

            else:
                fail_count += 1
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync Customer Type {ct['customer_type_name']}."
                )
                frappe.logger().error(f"Failed to sync Customer Type {ct['name']}: {response}")
                publish(
                    KEY_REALTIME["key_realtime_categories"],
                    f"Failed to sync Customer Type {ct['customer_type_name']}.",
                    error=True,
                )

        frappe.db.commit()

        # Tổng kết
        message = f"Customer Type sync completed. Success: {success_count}, Failed: {fail_count}"
        status = "Success" if fail_count == 0 else "Partial Success"

        create_dms_log(status=status, message=message)
        publish(KEY_REALTIME["key_realtime_categories"], message, done=True)

        return {"message": message}

    except Exception as e:
        frappe.db.rollback()
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer types.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}

    
# Đồng bộ danh sách nhóm khách hàng
def sync_customer_group():
    if enable_dms:
        frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_group_job", queue="long", timeout=300, key=KEY_REALTIME["key_realtime_categories"])
        return {"message": "Customer Group Sync job has been queued."}

@frappe.whitelist()
def sync_customer_group_job(*args, **kwargs):
    try:
        create_dms_log(status="Queued", message="Customer Group sync job started.")

        # Lấy danh sách Customer Group chưa đồng bộ
        customer_groups = frappe.get_all(
            "DMS Customer Group",
            filters={"is_sync": False},
            fields=["name", "customer_group", "name_customer_group"]
        )

        if not customer_groups:
            create_dms_log(status="Skipped", message="No new customer groups to sync.")
            publish(KEY_REALTIME["key_realtime_categories"], "No new customer groups to sync.", done=True)
            return {"message": "No new data to sync."}

        # Khởi tạo DMS API client
        dms_client = DMSApiClient()

        success_count = 0
        fail_count = 0

        # Lặp từng nhóm khách hàng để gửi request riêng
        for idx, cg in enumerate(customer_groups, start=1):
            request_payload = {
                "stt": idx,
                "ma": cg.get("customer_group") or "",
                "ten": cg.get("name_customer_group") or "",
                "trang_thai": True
            }

            # Ghi log từng request
            create_dms_log(
                status="Processing",
                method="POST",
                request_data=request_payload
            )

            # Gửi từng bản ghi lên DMS
            response, success = dms_client.request(
                endpoint="/OpenAPI/V1/CustomerGroup",
                method="POST",
                body=request_payload
            )

            # Xử lý kết quả từng bản ghi
            if response.get("status"):
                frappe.db.set_value("DMS Customer Group", cg["name"], "is_sync", True)
                success_count += 1

                create_dms_log(
                    status="Success",
                    response_data=response,
                    message=f"Customer Group {cg['name_customer_group']} synced successfully."
                )
                publish(
                    KEY_REALTIME["key_realtime_categories"],
                    f"Synced Customer Group {cg['name_customer_group']} successfully.",
                )

            else:
                fail_count += 1
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message=f"Failed to sync Customer Group {cg['name_customer_group']}."
                )
                frappe.logger().error(f"Failed to sync Customer Group {cg['name']}: {response}")
                publish(
                    KEY_REALTIME["key_realtime_categories"],
                    f"Failed to sync Customer Group {cg['name_customer_group']}.",
                    error=True,
                )

        frappe.db.commit()

        # Tổng kết
        message = f"Customer Group sync completed. Success: {success_count}, Failed: {fail_count}"
        status = "Success" if fail_count == 0 else "Partial Success"

        create_dms_log(status=status, message=message)
        publish(KEY_REALTIME["key_realtime_categories"], message, done=True)

        return {"message": message}

    except Exception as e:
        frappe.db.rollback()
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer groups.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        publish(KEY_REALTIME["key_realtime_categories"], f"Sync Error: {str(e)}", error=True)
        return {"error": str(e)}
    

@frappe.whitelist(methods="POST")
def create_customers(**kwargs):
    try:
        # Nhận dữ liệu
        raw_data = kwargs.get("data") or frappe.form_dict.get("data")

        if isinstance(raw_data, bytes):
            raw_data = json.loads(raw_data.decode("utf-8"))
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
        if isinstance(raw_data, list):
            data = {"data": raw_data}
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
            frappe.throw("Dữ liệu truyền lên không hợp lệ.")

        customers_data = data.get("data", [])

        if not customers_data:
            frappe.throw(_("Không có dữ liệu khách hàng để xử lý."))

        results = []

        for raw in customers_data:
            try:
                item = frappe._dict(raw)
                customer_code = item.get("makh")
                customer_name = item.get("tenkh")

                if not customer_code or not customer_name:
                    raise ValueError("Thiếu Mã KH hoặc Tên KH")

                create_dms_log(
                    status="Processing",
                    method="POST",
                    request_data=item,
                    message=f"Đang xử lý khách hàng {customer_name} ({customer_code})"
                )

                existing = frappe.db.exists("Customer", {"customer_code_dms": customer_code})

                # --- Cập nhật ---
                if existing:
                    cust = frappe.get_doc("Customer", existing)
                    cust.customer_name = customer_name
                    cust.customer_details = item.get("trang_thai_kh")
                    cust.dms_customer_group = item.get("nhom_kh")
                    cust.dms_customer_type = item.get("loai_kh")
                    cust.sfa_sale_channel = item.get("kenh")
                    cust.mobile_no = item.get("sdt")
                    cust.email_id = item.get("email")
                    cust.custom_credit_limit = item.get("han_muc_cn")
                    cust.custom_birthday = parse_date(item.get("sinh_nhat"))
                    cust.is_sync = 1

                    credit_limit_value = item.get("han_muc_cn")
                    if credit_limit_value:
                        cust.set("credit_limits", [])
                        cust.append("credit_limits", {
                            "company": frappe.defaults.get_global_default("company") or "Vinamilk",
                            "credit_limit": credit_limit_value,
                            "bypass_credit_limit_check": 0
                        })

                    cust.save(ignore_permissions=True)

                    create_dms_log(
                        status="Updated",
                        response_data={"customer": cust.name},
                        message=f"Customer {customer_code} updated successfully."
                    )

                    results.append({"makh": customer_code, "status": "Updated"})
                    continue

                # --- Tạo mới ---
                customer = frappe.new_doc("Customer")
                customer.customer_code_dms = customer_code
                customer.customer_name = customer_name
                customer.customer_details = item.get("trang_thai_kh")
                customer.dms_customer_group = item.get("nhom_kh")
                customer.dms_customer_type = item.get("loai_kh")
                customer.sfa_sale_channel = item.get("kenh")
                customer.mobile_no = item.get("sdt")
                customer.email_id = item.get("email")
                customer.custom_credit_limit = item.get("han_muc_cn")
                customer.custom_birthday = parse_date(item.get("sinh_nhat"))
                customer.customer_type = "Company"
                customer.is_sales_dms = 1
                customer.is_sync = 1

                if item.get("han_muc_cn"):
                    customer.set("credit_limits", [])
                    customer.append("credit_limits", {
                        "company": frappe.defaults.get_global_default("company"),
                        "credit_limit": item.get("han_muc_cn"),
                        "bypass_credit_limit_check": 0
                    })

                customer.insert(ignore_permissions=True)

                # --- Address ---
                if item.get("dia_chi"):
                    city_name = extract_city_from_address(item.get("dia_chi"))
                    if city_name:
                        address = frappe.new_doc("Address")
                        address.address_title = customer_name
                        address.address_line1 = item.get("dia_chi")
                        address.city = city_name
                        address.country = "Vietnam"
                        address.address_type = "Billing"
                        address.append("links", {
                            "link_doctype": "Customer",
                            "link_name": customer.name
                        })
                        address.insert(ignore_permissions=True)
                        customer.customer_primary_address = address.name
                        customer.primary_address = address.address_title
                        customer.save(ignore_permissions=True)


                # --- Contact ---
                if item.get("nguoi_lien_he"):
                    contact = frappe.new_doc("Contact")
                    contact.first_name = item.get("nguoi_lien_he")
                    contact.designation = item.get("chuc_vu")
                    contact.is_primary_contact = 1
                    contact.is_billing_contact = 1
                    if item.get("sdt"):
                        contact.append("phone_nos", {
                            "phone": item.get("sdt"),
                            "is_primary_phone": 1,
                            "is_primary_mobile_no": 1
                        })
                    contact.email_id = item.get("email")
                    contact.append("links", {
                        "link_doctype": "Customer",
                        "link_name": customer.name
                    })
                    contact.insert(ignore_permissions=True)
                    customer.customer_primary_contact = contact.name
                    customer.save(ignore_permissions=True)

                frappe.db.commit()

                create_dms_log(
                    status="Success",
                    response_data={"customer": customer.name},
                    message=f"Customer {customer_code} created successfully."
                )

                results.append({"makh": customer_code, "status": "Created"})

            except Exception as e:
                frappe.db.rollback()
                error_message = f"Lỗi xử lý khách hàng {item.get('makh')}: {str(e)}"
                create_dms_log(status="Failed", request_data=item, message=error_message)
                frappe.log_error(frappe.get_traceback(), f"Customer Sync Error: {item.get('makh')}")
                results.append({"makh": item.get("makh"), "status": "Failed", "error": str(e)})

        frappe.db.commit()
        return {
            "status": "ok",
            "results": results
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.throw(_("Lỗi xử lý danh sách khách hàng: {0}").format(str(e)))


# HÀM HỖ TRỢ
def parse_date(value):
    """Chuyển đổi ISO date (chuỗi từ DMS) sang Python datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    
def extract_city_from_address(address: str) -> str | None:
    """Lấy phần cuối cùng của địa chỉ và kiểm tra có trong DMS Province không"""
    if not address:
        return None

    try:
        # Lấy phần cuối cùng sau dấu '-'
        parts = [p.strip() for p in address.split('-') if p.strip()]
        if not parts:
            return None

        possible_city = parts[-1]

        # Kiểm tra trong DMS Province
        province = frappe.db.get_value("DMS Province", {"province_name": possible_city}, "province_name")
        if province:
            return province
        return None
    except Exception:
        return None


    
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
    codes_str = ";".join(customer_codes)

    request_payload = {
        "ma": codes_str
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
            endpoint="/OpenAPI/V1/Customer",
            method="DELETE",
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