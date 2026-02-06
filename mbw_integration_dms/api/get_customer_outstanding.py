import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_customer_outstanding(
    customer_code_dms=None,
    company=None,
    page=1,
    page_size=2000
):
    """
    Lấy công nợ cuối (outstanding amount) của khách hàng có công nợ (> 0), với phân trang và lọc.

    Args:
        customer_code_dms (str, optional): Mã khách hàng DMS để lọc
        company (str, optional): Tên công ty để lọc (nếu không truyền sẽ dùng company mặc định)
        page (int, optional): Số trang (mặc định: 1)
        page_size (int, optional): Số bản ghi mỗi trang (mặc định: 2000)

    Returns:
        dict: Chỉ khách hàng có outstanding_amount > 0:
            - data: Danh sách khách hàng
            - total: Tổng số khách hàng
            - page: Trang hiện tại
            - page_size: Số bản ghi mỗi trang
            - total_pages: Tổng số trang
    """
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 2000

    page = max(1, page)
    page_size = max(1, min(page_size, 2000))

    offset = (page - 1) * page_size

    if not company:
        company = frappe.defaults.get_global_default("company")

    where_conditions = []
    params = []

    if customer_code_dms:
        where_conditions.append("c.customer_code_dms = %s")
        params.append(customer_code_dms)

    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

    join_conditions = "si.customer = c.name AND si.docstatus = 1 AND si.outstanding_amount > 0"
    join_params = []

    if company:
        join_conditions += " AND si.company = %s"
        join_params.append(company)

    # Chỉ đếm khách hàng có ít nhất 1 SI outstanding > 0
    count_query = f"""
        SELECT COUNT(DISTINCT c.name) as total
        FROM `tabCustomer` c
        INNER JOIN `tabSales Invoice` si ON {join_conditions}
        WHERE 1=1 {where_clause}
    """

    count_params = list(join_params) + params
    total_result = frappe.db.sql(count_query, tuple(count_params), as_dict=True)
    total = total_result[0].get("total", 0) if total_result else 0

    default_currency = frappe.defaults.get_global_default("currency") or "VND"

    # Chỉ lấy khách hàng có outstanding_amount > 0 (INNER JOIN)
    query = f"""
        SELECT
            c.name as customer,
            c.customer_name,
            c.customer_code_dms,
            SUM(si.outstanding_amount) as outstanding_amount,
            COALESCE(MAX(si.currency), c.default_currency, %s) as currency
        FROM `tabCustomer` c
        INNER JOIN `tabSales Invoice` si ON {join_conditions}
        WHERE 1=1 {where_clause}
        GROUP BY c.name, c.customer_name, c.customer_code_dms, c.default_currency
        ORDER BY c.customer_name
        LIMIT %s OFFSET %s
    """

    query_params = [default_currency] + list(join_params) + params + [page_size, offset]
    customers = frappe.db.sql(query, tuple(query_params), as_dict=True)

    data = []
    for customer in customers:
        data.append({
            "customer": customer.get("customer"),
            "customer_name": customer.get("customer_name"),
            "customer_code_dms": customer.get("customer_code_dms"),
            "outstanding_amount": flt(customer.get("outstanding_amount"), 2),
            "currency": customer.get("currency") or default_currency
        })

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }