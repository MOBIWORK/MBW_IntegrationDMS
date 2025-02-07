import frappe

from mbw_integration_dms.mbw_integration_dms.brand import sync_brand
from mbw_integration_dms.mbw_integration_dms.channel import sync_channel
from mbw_integration_dms.mbw_integration_dms.customer import sync_customer_type, \
    sync_customer_group
from mbw_integration_dms.mbw_integration_dms.industry import sync_industry
from mbw_integration_dms.mbw_integration_dms.provider import sync_provider
from mbw_integration_dms.mbw_integration_dms.region import sync_region
from mbw_integration_dms.mbw_integration_dms.unit import sync_unit

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
    pass

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
    return {"message": "Sync all category job has been queued."}