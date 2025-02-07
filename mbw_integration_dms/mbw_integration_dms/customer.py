import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


def sync_customer():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_job", queue="long", timeout=300)
    return {"message": "Customer Sync job has been queued."}

def sync_customer_job():
    pass

# Đồng bộ danh sách loại khách hàng
def sync_customer_type():
    """
    Đưa job vào hàng đợi để đồng bộ Customer Type
    """
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_type_job", queue="long", timeout=300)
    return {"message": "Customer Type Sync job has been queued."}

def sync_customer_type_job():
    try:
        create_dms_log(status="Queued", message="Customer Type sync job started.")

        # Lấy danh sách Customer Type chưa đồng bộ
        customer_types = frappe.get_all(
            "Customer Type",
            filters={"is_sync": False},
            fields=["customer_type_id", "customer_type_name", "is_sync"]
        )

        if not customer_types:
            create_dms_log(status="Skipped", message="No new customer types to sync.")
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["customer_type_id"],  # Mã danh mục
                "name": ct["customer_type_name"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in customer_types
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "CustomerType",
            "orgid": dms_client.orgid,
            "data": formatted_data
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if success:
            for ct in customer_types:
                frappe.db.set_value("Customer Type", {"customer_type_id": ct["customer_type_id"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Customer Types synced successfully."
            )
            return {"message": "Customer Types synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync customer types."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer types.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}
    

# Đồng bộ danh sách nhóm khách hàng

def sync_customer_group():
    frappe.enqueue("mbw_integration_dms.mbw_integration_dms.customer.sync_customer_group_job", queue="long", timeout=300)
    return {"message": "Customer Group Sync job has been queued."}


def sync_customer_group_job():
    try:
        create_dms_log(status="Queued", message="Customer Type sync job started.")

        # Lấy danh sách Customer Group chưa đồng bộ
        customer_groups = frappe.get_all(
            "DMS Customer Group",
            filters={"is_sync": False},
            fields=["customer_group", "name_customer_group", "is_sync"]
        )

        if not customer_groups:
            create_dms_log(status="Skipped", message="No new customer group to sync.")
            return {"message": "No new data to sync."}

        # Khởi tạo API Client
        dms_client = DMSApiClient()

        formatted_data = [
            {
                "code": ct["customer_group"],  # Mã danh mục
                "name": ct["name_customer_group"],  # Tên danh mục
                "isActive": True  # Trạng thái danh mục (mặc định True)
            }
            for ct in customer_groups
        ]

        # Dữ liệu gửi đi
        request_payload = {
            "category": "CustomerGroup",
            "orgid": dms_client.orgid,
            "data": formatted_data
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/CategorySync",
            method="POST",
            body=request_payload
        )

        # Nếu thành công, cập nhật is_sync = True
        if success:
            for ct in customer_groups:
                frappe.db.set_value("DMS Customer Group", {"customer_groupct": ["customer_group"]}, "is_sync", True)
            frappe.db.commit()

            create_dms_log(
                status="Success",
                response_data=response,
                message="Customer Group synced successfully."
            )
            return {"message": "Customer Group synced successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to sync customer group."
            )
            frappe.logger().error(f"Failed to sync: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while syncing customer groups.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}