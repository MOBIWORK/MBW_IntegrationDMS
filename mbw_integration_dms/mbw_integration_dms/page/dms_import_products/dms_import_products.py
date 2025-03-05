import frappe
from mbw_integration_dms.mbw_integration_dms.kpi import get_kpi_dms
from mbw_integration_dms.mbw_integration_dms.product import sync_product
from mbw_integration_dms.mbw_integration_dms.timesheets import get_timesheet_dms


@frappe.whitelist()
def get_products(page):
    page_size = 20
    start_idx = (int(page) - 1) * page_size
    query = f"""
                SELECT 
                    i.name, i.item_code, i.item_name, i.is_sync
                FROM `tabItem` i
                WHERE 
                    i.is_sale_dms = 1 
                    AND i.is_sync = 0

                ORDER BY i.item_code
                LIMIT {start_idx}, {page_size}
            """
    data = frappe.db.sql(query, as_dict=True)
    return data

@frappe.whitelist()
def get_count_products():
    try:
        erpnextCount = frappe.db.count(
            "Item",
            filters={"is_sale_dms": True},
        )
        syncedCount = frappe.db.count(
            "Item",
            filters={"is_sale_dms": True, "is_sync": True},
        )
        pendingCount = erpnextCount - syncedCount
        data = {
            "erpnextCount": erpnextCount,
            "pendingCount": pendingCount,
            "syncedCount": syncedCount,
        }
        return data
    except Exception as e:
            return e

@frappe.whitelist()
def sync_all_products():
    return sync_product()

@frappe.whitelist()
def get_sales_orders(page):
    page_size = 20
    start_idx = (int(page) - 1) * page_size
    query = f"""
                SELECT 
                    so.name, so.is_sync
                FROM `tabSales Order` so
                WHERE 
                    so.is_sales_dms = 1 
                    AND so.is_sync = 0

                ORDER BY so.name
                LIMIT {start_idx}, {page_size}
            """
    data = frappe.db.sql(query, as_dict=True)
    return data

@frappe.whitelist()
def get_dms_kpi():
    return get_kpi_dms()

@frappe.whitelist()
def get_dms_timesheet():
    return get_timesheet_dms()