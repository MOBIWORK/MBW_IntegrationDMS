import json
import os
import datetime

import frappe
from frappe import _, new_doc

CATEGORY_DOCTYPE = ["Brand", "Industry Type", "UOM", "Customer Type", "DMS Customer Group", "Territory", "Channel", "Warehouse", "Supplier"]
CATEGORIES = ["Brand", "Industry", "Unit", "CustomerType", "CustomerGroup", "Region", "Channel", "Warehouse", "Provider"]
@frappe.whitelist()
def auto_add_category():
    import_master_data()
    pass

def import_master_data():
    # xoa cac brand dang ton tai
    file_path = os.path.join(frappe.get_app_path('mbw_integration_dms'), 'config', 'master_data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as ex:
        frappe.log_error(f"Error reading master_data.json: {ex}")
        return False
    for idx, category in enumerate(CATEGORY_DOCTYPE):
        if category not in ["Warehouse", "Territory"]:
            try:
                frappe.db.delete(category)
                frappe.db.commit()
            except Exception as ex:
                return False
        # elif category == "Warehouse":
        #     try:
        #         frappe.db.sql("""
        #                 DELETE FROM `tabWarehouse`
        #                 WHERE name != 'All Warehouses - M'
        #             """)
        #         frappe.db.commit()
        #     except Exception as ex:
        #         frappe.log_error(f"Error deleting warehouses: {ex}")
        #         return False
        elif category == "Territory":
            try:
                frappe.db.sql("""
                        DELETE FROM `tabTerritory`
                        WHERE name != 'Tất cả khu vực'
                    """)
                frappe.db.commit()
            except Exception as ex:
                frappe.log_error(f"Error deleting territory: {ex}")
                return False
        if CATEGORIES[idx] in data:
            data_category = data[CATEGORIES[idx]]
            for d in data_category:
                element = {
                           'owner': 'Administrator',
                           'creation': datetime.datetime.now(),
                           'modified': datetime.datetime.now(),
                           'modified_by': 'Administrator',
                           'docstatus': 0,
                           'is_sync': 0,
                           }
                if category == "Brand":
                    element['name'] = d["Mã"]
                    element['brand'] = d["Tên"]

                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabBrand` (`name`, `brand`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`)
                                    VALUES (%(name)s, %(brand)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting brand {d}: {ex}")
                elif category == "Industry Type":
                    element['name'] = d["Mã"]
                    element['industry'] = d["Tên"]
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabIndustry Type` (`name`, `industry`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`)
                                    VALUES (%(name)s, %(industry)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting industry {d}: {ex}")
                elif category == "UOM":
                    element['name'] = d["Mã"]
                    element['uom_name'] = d["Tên"]
                    element['enabled'] = 1
                    element['must_be_whole_number']= 0
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabUOM` (`name`, `uom_name`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`, `enabled`, `must_be_whole_number`)
                                    VALUES (%(name)s, %(uom_name)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s, %(enabled)s, %(must_be_whole_number)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting uom {d}: {ex}")
                elif category == "Customer Type":
                    element['customer_type_id'] = d["Mã"]
                    element['customer_type_name'] = d["Tên"]
                    element['name'] = d["Tên"]
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabCustomer Type` (`name`, `customer_type_id`,`customer_type_name`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`)
                                    VALUES (%(name)s, %(customer_type_id)s,  %(customer_type_name)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting Customer Type {d}: {ex}")
                elif category == "DMS Customer Group":
                    element['customer_group'] = d["Ưu Tiên"]
                    element['name_customer_group'] = d["Bán Buôn"]
                    element['name'] = d["Ưu Tiên"]
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabDMS Customer Group` (`name`, `customer_group`,`name_customer_group`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`)
                                    VALUES (%(name)s, %(customer_group)s,  %(name_customer_group)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting industry {d}: {ex}")
                elif category == "Channel":
                    element['channel_name'] = d["Mã"]
                    element['channel_code'] = d["Tên"]
                    element['name'] = d["Mã"]
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabChannel` (`name`, `channel_name`,`channel_code`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`)
                                    VALUES (%(name)s, %(channel_name)s,  %(channel_code)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting DMS Customer Group {d}: {ex}")
                elif category == "Warehouse":
                    element['name'] = d["Mã"]
                    element['warehouse_name'] = d["Tên"]
                    element['parent_warehouse'] = "All Warehouses - M"
                    element['lft'] = 12
                    element['rgt'] = 12
                    doc_all = frappe.get_doc("Warehouse", "All Warehouses - M").as_dict()
                    element['company'] = doc_all.company
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabWarehouse` (`name`, `warehouse_name`,`parent_warehouse`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`, `lft`, `rgt`, `company`)
                                    VALUES (%(name)s, %(warehouse_name)s,  %(parent_warehouse)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s, %(lft)s, %(rgt)s, %(company)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting warehouse {d}: {ex}")
                elif category == "Territory":
                    element['name'] = d["Mã"]
                    element['territory_name'] = d["Tên"]
                    element['parent_territory'] = d["Mã cha"]
                    element["is_group"] = d["is_group"] if "is_group" in d else 0
                    element['lft'] = 12
                    element['rgt'] = 12
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabTerritory` (`name`, `territory_name`,`parent_territory`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`,`is_group`, `lft`, `rgt`)
                                    VALUES (%(name)s, %(territory_name)s,  %(parent_territory)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s, %(is_group)s, %(lft)s, %(rgt)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting Territory {d}: {ex}")
                elif category == "Supplier":
                    element['name'] = d["Mã"]
                    element['supplier_name'] = d["Tên"]
                    element['mobile_no'] = d["SĐT"] if "SĐT" in d else None
                    element['tax_id'] = d["Mã số thuế"] if "Mã số thuế" in d else None
                    element['primary_address'] = d["Địa chỉ"] if "Địa chỉ" in d else None
                    element['country'] = 'Vietnam'
                    try:
                        frappe.db.sql("""
                                    INSERT INTO `tabSupplier` (`name`, `supplier_name`,`mobile_no`, `owner`, `creation`, `modified`, 
                                    `modified_by`, `docstatus`, `is_sync`,`tax_id`, `primary_address`, `country`)
                                    VALUES (%(name)s, %(supplier_name)s,  %(mobile_no)s, %(owner)s, %(creation)s, %(modified)s, 
                                    %(modified_by)s, %(docstatus)s, %(is_sync)s, %(tax_id)s, %(primary_address)s, %(country)s)
                                """, element)
                    except Exception as ex:
                        frappe.log_error(f"Error inserting Territory {d}: {ex}")
    frappe.utils.nestedset.rebuild_tree("Warehouse")
    frappe.utils.nestedset.rebuild_tree('Territory')
    frappe.db.commit()
    return True
