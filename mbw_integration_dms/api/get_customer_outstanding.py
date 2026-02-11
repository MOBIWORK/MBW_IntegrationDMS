import frappe
from frappe import _
from frappe.utils import flt

# TTL mặc định (giây). 0 = không cache.
DEFAULT_CACHE_TTL = 300  # 5 phút

def _cache_key(customer_code_dms, company, from_date, page, page_size):
    """Tạo key cache từ tham số."""
    parts = [
        "customer_outstanding",
        company or "",
        customer_code_dms or "",
        from_date or "",
        page,
        page_size,
    ]
    return ":".join(str(p) for p in parts)

@frappe.whitelist()
def get_customer_outstanding(
    customer_code_dms=None,
    company=None,
    from_date=None,
    page=1,
    page_size=2000,
    cache_ttl=None
):
    """
    Lấy công nợ cuối (outstanding amount) của khách hàng có công nợ (> 0), có cache.
    Nếu truyền from_date: chỉ trả về khách hàng có thay đổi công nợ từ ngày đó trở đi,
    nhưng số công nợ là tổng hiện tại (mọi hóa đơn outstanding).

    Args:
        customer_code_dms (str, optional): Mã khách hàng DMS để lọc
        company (str, optional): Tên công ty để lọc
        from_date (str, optional): Chỉ lấy khách hàng có Sales Invoice modified >= from_date
        page (int, optional): Số trang (mặc định: 1)
        page_size (int, optional): Số bản ghi mỗi trang (mặc định: 2000)
        cache_ttl (int, optional): Thời gian cache (giây). 0 = tắt cache. None = dùng mặc định (300).
    """
    # Chuẩn hóa page, page_size
    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        page = 1
        page_size = 2000

    # Chuẩn hóa cache_ttl
    if cache_ttl is None:
        cache_ttl = DEFAULT_CACHE_TTL
    else:
        try:
            cache_ttl = int(cache_ttl)
        except (ValueError, TypeError):
            cache_ttl = DEFAULT_CACHE_TTL

    # Key cache phụ thuộc cả from_date
    key = _cache_key(customer_code_dms, company, from_date, page, page_size)

    # Đọc cache nếu bật
    if cache_ttl > 0:
        cached = frappe.cache().get_value(key)
        if cached is not None:
            return cached

    page = max(1, page)
    page_size = max(1, min(page_size, 2000))
    offset = (page - 1) * page_size

    if not company:
        company = frappe.defaults.get_global_default("company")

    # WHERE cho Customer
    where_conditions = []
    params = []
    if customer_code_dms:
        where_conditions.append("c.customer_code_dms = %s")
        params.append(customer_code_dms)
    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

    # JOIN để tính tổng công nợ hiện tại (mọi hóa đơn outstanding)
    join_conditions = "si.customer = c.name AND si.docstatus = 1 AND si.outstanding_amount > 0"
    join_params = []
    if company:
        join_conditions += " AND si.company = %s"
        join_params.append(company)

    # EXISTS để lọc khách hàng có thay đổi từ from_date trở đi
    exists_clause = ""
    exists_params = []
    if from_date:
        exists_conditions = "si2.customer = c.name AND si2.docstatus = 1"
        if company:
            exists_conditions += " AND si2.company = %s"
            exists_params.append(company)
        exists_conditions += " AND si2.modified >= %s"
        exists_params.append(from_date)

        exists_clause = f"""
            AND EXISTS (
                SELECT 1 FROM `tabSales Invoice` si2
                WHERE {exists_conditions}
            )
        """

    # Đếm số customer
    count_query = f"""
        SELECT COUNT(DISTINCT c.name) as total
        FROM `tabCustomer` c
        INNER JOIN `tabSales Invoice` si ON {join_conditions}
        WHERE 1=1 {where_clause}
        {exists_clause}
    """
    count_params = list(join_params) + exists_params + params
    total_result = frappe.db.sql(count_query, tuple(count_params), as_dict=True)
    total = total_result[0].get("total", 0) if total_result else 0

    # Lấy danh sách customer với tổng công nợ hiện tại
    default_currency = frappe.defaults.get_global_default("currency") or "VND"
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
        {exists_clause}
        GROUP BY c.name, c.customer_name, c.customer_code_dms, c.default_currency
        ORDER BY c.customer_name
        LIMIT %s OFFSET %s
    """
    query_params = [default_currency] + list(join_params) + exists_params + params + [page_size, offset]
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
    result = {
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }

    # Ghi cache
    if cache_ttl > 0:
        frappe.cache().set_value(key, result, expires_in_sec=cache_ttl)

    return result