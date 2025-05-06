import frappe
from frappe import _
from frappe.utils import get_datetime

@frappe.whitelist()
def get_projected_qty(item_code=None, last_updated=None):
    """
    Lấy số lượng dự báo (Projected Qty) của item trong tất cả các kho hợp lệ.
    - Nếu truyền `item_code`, lấy dữ liệu của item đó.
    - Nếu không truyền `item_code`, lấy tất cả items.
    - Nếu truyền `last_updated`, chỉ lấy dữ liệu từ thời gian đó trở đi.
    - Chỉ lấy dữ liệu từ những kho hợp lệ (không bị vô hiệu hóa).
    """
    filters = {}

    # Lọc theo item_code nếu được truyền vào
    if item_code:
        filters["item_code"] = item_code

    # Lọc theo thời gian cập nhật nếu được truyền vào
    if last_updated:
        try:
            filters["modified"] = [">=", get_datetime(last_updated)]
        except Exception:
            frappe.throw(_("Thời gian không hợp lệ. Định dạng đúng: YYYY-MM-DD HH:MM:SS"))

    # Lấy danh sách warehouses hợp lệ (không bị disabled)
    valid_warehouses = frappe.get_all("Warehouse", filters={"disabled": 0, "is_sale_dms": 1}, pluck="name")

    bins = frappe.get_all(
        "Bin",
        filters=filters,
        fields=["item_code", "warehouse", "projected_qty", "stock_uom", "modified"]
    )

    # Tạo dictionary kết quả, nhóm theo item_code
    result = {}
    for bin in bins:
        item_code = bin["item_code"]
        warehouse = bin["warehouse"]

        if warehouse in valid_warehouses:
            if item_code not in result:
                result[item_code] = []
            
            result[item_code].append({
                "warehouse": warehouse,
                "projected_qty": int(bin["projected_qty"]) if int(bin["projected_qty"] > 0) else 0,
                "uom": bin["stock_uom"],
                "last_updated": bin["modified"]
            })

    return result