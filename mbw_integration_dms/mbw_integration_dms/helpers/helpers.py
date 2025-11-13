# Copyright (c) 2025, Tuanbd MBWD
# For license information, please see LICENSE

import frappe
import pydash
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import check_enable_integration_dms


enable_dms = check_enable_integration_dms()

# Xử lý thêm mới/cập nhật địa chỉ
def create_address_customer(address_info, link_to_customer):
    try:
        key_info = {
            "address_title", "address_type", "address_line1", "city", "is_primary_address", "is_shipping_address"
        }
        address_info = frappe._dict(address_info)
        id_address = address_info.get("name") or False
        address_title_filter = {"address_title": ["like", f"%{address_info.address_title}%"]}

        # Kiểm tra sự tồn tại của address_title trong các Address khác
        exit_address_title = frappe.db.exists("Address", {**address_title_filter, "name": ["!=", id_address]})

        # Nếu có ID Address, tìm tài liệu hiện có hoặc tạo mới nếu chưa tồn tại
        doc_address = frappe.get_doc("Address", id_address) if id_address and frappe.db.exists("Address", id_address) else None

        if doc_address:
            # Nếu địa chỉ với cùng title đã tồn tại, cập nhật thông tin mới
            if exit_address_title:
                update_address(doc_address, address_info, key_info, link_to_customer)
                curent_address = frappe.get_doc("Address", address_title_filter)
                if link_to_customer:
                    curent_address.append("links", link_to_customer)
                curent_address.save()
                frappe.db.commit()
                return curent_address
            else:
                update_address(doc_address, address_info, key_info)
                frappe.db.commit()
                return doc_address
        else:
            # Nếu không có tài liệu Address, tạo mới hoặc cập nhật địa chỉ hiện có
            curent_address = frappe.get_doc("Address", address_title_filter) if exit_address_title else frappe.new_doc("Address")
            update_address(curent_address, address_info, key_info)
            if link_to_customer:
                curent_address.append("links", link_to_customer)
            curent_address.save() if exit_address_title else curent_address.insert()
            frappe.db.commit()
            return curent_address

    except Exception:
        return None    
    
def update_address(doc, info, keys, link_to_doctype=None):
    for key, value in info.items():
        if key in keys:
            doc.set(key, value)
            
    if link_to_doctype:
        links = pydash.filter_(doc.get("links"), lambda x: x.get("link_doctype") != link_to_doctype.get("link_doctype") and x.get("link_name") != link_to_doctype.get("link_name"))
        doc.set("links", links)

# Tạo log bên partner
def create_partner_log(id_log_dms, status, title, message=""):
    dms_client = DMSApiClient()

    payload = {
        "orgid": dms_client.orgid,
        "id": id_log_dms,
        "status": status,
        "title": title,
        "message": message
    }

    try:
        response = dms_client.request(
            endpoint="/sync_log",
            method="POST",
            body=payload
        )
        return response.json()
    
    except Exception as e:
        frappe.logger().error(f"Lỗi gửi log đến DMS: {str(e)}")
        return {"error": str(e)}

# Cập nhật trạng thái đơn bên DMS
def update_dms_order_status(doc):
    """Gửi API cập nhật trạng thái SO bên DMS khi trạng thái SO thay đổi thành 'Delivered'."""
    dms_client = DMSApiClient()
    
    payload = {
        "ma_phieu": doc.dms_so_code,
        "trang_thai": "Đã giao hàng",
    }

    try:
        response = dms_client.request(
            endpoint="/OpenAPI/V1/Order",
            method="PUT",
            body=payload
        )
        return response.json()

    except Exception as e:
        frappe.logger().error(f"Failed to update DMS order for SO {doc.name}: {str(e)}")

def on_sales_order_update(doc, method):
    """Kiểm tra nếu trạng thái thay đổi thành 'Delivered' thì gọi API cập nhật DMS."""
    if enable_dms and doc.is_sale_dms and doc.get("delivery_status") != doc.get_db_value("delivery_status") and doc.delivery_status == "Fully Delivered":
        update_dms_order_status(doc)

def update_stt_so_cancel(doc, method):
    if enable_dms:
        dms_client = DMSApiClient()
        if doc.is_sale_dms:
            payload = {
                "ma_phieu": doc.dms_so_code,
                "trang_thai": "Từ chối",
            }

            try:
                response = dms_client.request(
                    endpoint="/OpenAPI/V1/Order",
                    method="PUT",
                    body=payload
                )
                return response.json()

            except Exception as e:
                frappe.logger().error(f"Failed to update DMS order for SO {doc.name}: {str(e)}")


def publish(key, message, synced=False, error=False, done=False, br=True):
    frappe.publish_realtime(
		key,
		{
			"synced": synced,
			"error": error,
			"message": message + ("<br /><br />" if br else ""),
			"done": done,
		},
	)