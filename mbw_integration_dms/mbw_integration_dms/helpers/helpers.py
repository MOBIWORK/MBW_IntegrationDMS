import json
import frappe
from bs4 import BeautifulSoup
from frappe import _
from datetime import datetime
import pydash


# Xử lý thêm mới/cập nhật địa chỉ
def create_address_customer(address_info, link_to_customer):
    try:
        key_info = ["address_title", "address_type", "address_line1", "city", "county", "state", "is_primary_address", "is_shipping_address", "address_location"]
        address_info = frappe._dict(address_info)
        id_address = address_info.name if address_info.name and address_info.name != "" else False
        exit_address_title = frappe.db.exists("Address", {"address_title": ["like", f"%{address_info.address_title}%"], "name": ["!=", id_address]})
        if id_address and frappe.db.exists("Address", id_address):
            doc_address = frappe.get_doc("Address", id_address)
            # kiểm tra đã tồn tại address muốn đối sang chưa
            if exit_address_title: 
                for key, value in address_info.items():
                    if key in key_info:
                        doc_address.set(key,value)
                links = doc_address.get("links")
                if len(link_to_customer) > 0:
                    links = pydash.filter_(links, lambda x: x.get("link_doctype") != link_to_customer.get("link_doctype") and x.get("link_name") != link_to_customer.get("link_name"))
                # Xóa khách ở địa chỉ cũ nếu có nhiều khách , xóa luôn địa chỉ nếu chỉ có 1 khách liên kết
                doc_address.set("links", links)
                doc_address.save()
                curent_address = frappe.get_doc("Address", {"address_title": ["like", f"%{address_info.address_title}%"]})
                if len(link_to_customer) > 0:
                    curent_address.append("links", link_to_customer)
                curent_address.save()
                frappe.db.commit()
                return curent_address
            else:
                for key, value in address_info.items():
                    if key in key_info:
                        doc_address.set(key, value)
                doc_address.save()
                frappe.db.commit()
                return doc_address
        else:
            if exit_address_title: 
                curent_address = frappe.get_doc("Address", {"address_title": ["like", f"%{address_info.address_title}%"]})
                for key, value in address_info.items():
                    if key in key_info:
                        curent_address.set(key, value)
                if len(link_to_customer) > 0:
                    curent_address.append("links", link_to_customer)
                curent_address.save()
                frappe.db.commit()
                return curent_address
            else:
                new_address = frappe.new_doc("Address")
                for key, value in address_info.items():
                    if key in key_info:
                        new_address.set(key, value)
                if len(link_to_customer) > 0:
                    new_address.append("links", link_to_customer)
                new_address.insert()
                frappe.db.commit()
                return new_address
            
    except Exception as e :
        return None    