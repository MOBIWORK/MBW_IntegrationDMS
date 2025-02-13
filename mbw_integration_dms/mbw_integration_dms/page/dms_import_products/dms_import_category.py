import frappe

from mbw_integration_dms.mbw_integration_dms.brand import sync_brand
from mbw_integration_dms.mbw_integration_dms.channel import sync_channel
from mbw_integration_dms.mbw_integration_dms.customer import sync_customer_type, \
    sync_customer_group, sync_customer
from mbw_integration_dms.mbw_integration_dms.industry import sync_industry
from mbw_integration_dms.mbw_integration_dms.provider import sync_provider
from mbw_integration_dms.mbw_integration_dms.region import sync_region
from mbw_integration_dms.mbw_integration_dms.unit import sync_unit
from mbw_integration_dms.mbw_integration_dms.warehouse import sync_warehouse

CATEGORY_DOCTYPE = ["Brand", "Industry Type", "Supplier", "UOM", "Customer Type", "DMS Customer Group", "Territory", "Channel", "Warehouse"]
CATEGORIES = ["Brand", "Industry", "Provider", "Unit", "CustomerType", "CustomerGroup", "Region", "Channel", "Warehouse"]

@frappe.whitelist()
def get_categories(page):
    page_size = 10
    start_idx = (int(page) - 1) * page_size
    data = []

    for idx, category in enumerate(CATEGORY_DOCTYPE):
        query = f"""
            SELECT name, is_sync
            FROM `tab{category}`
            WHERE is_sync = 0
            LIMIT {start_idx}, {page_size}
        """
        data_category = frappe.db.sql(query, as_dict=True)
        for d in data_category:
            d['doctype'] = category
            d['category'] = CATEGORIES[idx]
            data.append(d)
    return data

@frappe.whitelist()
def get_count_categories():
    erpnextCount = 0
    pendingCount = 0
    syncedCount = 0
    for idx, category in enumerate(CATEGORY_DOCTYPE):
        all_category = frappe.db.count(
            category
        )
        synced_category = frappe.db.count(
            category,
            filters={"is_sync": True},
        )
        erpnextCount += all_category
        syncedCount += synced_category
        pendingCount += all_category - synced_category
    data = {
        "erpnextCount": erpnextCount,
        "pendingCount": pendingCount,
        "syncedCount": syncedCount,
    }
    return data

@frappe.whitelist()
def sync_all_categories():
    sync_channel()
    sync_industry()
    sync_provider()
    sync_brand()
    sync_customer_type()
    sync_customer_group()
    sync_region()
    sync_unit()
    sync_warehouse()
    return {"message": "Sync all category job has been queued."}

@frappe.whitelist()
def get_customers(page):
    page_size = 20
    start_idx = (int(page) - 1) * page_size
    query = f"""
                SELECT 
                    c.customer_code_dms, c.customer_name, c.email_id, c.is_sync
                FROM `tabCustomer` c
                WHERE 
                    c.is_sales_dms = 1 
                    AND c.is_sync = 0

                ORDER BY c.customer_code_dms
                LIMIT {start_idx}, {page_size}
            """
    data = frappe.db.sql(query, as_dict=True)
    return data

@frappe.whitelist()
def get_count_customers():
    try:
        erpnextCount = frappe.db.count(
            "Customer",
            filters={"is_sales_dms": True},
        )
        syncedCount = frappe.db.count(
            "Customer",
            filters={"is_sales_dms": True, "is_sync": True},
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
def sync_all_customers():
    return sync_customer()
