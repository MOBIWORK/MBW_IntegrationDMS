# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


def create_delivery_note(doc, method):
    try:
        dms_client = DMSApiClient()

        id_dms = doc.id_dms
        ma_don = doc.sales_order
        kho_hang = doc.set_warehouse
        ck_don = doc.discount_amount
        items = doc.items
        san_pham = []

        for i in items:
            item = {
                "ma_sp": i.item_code,
                "dvt": i.uom,
                "sl": i.qty,
                "don_gia": i.price_list_rate,
                "ck": i.discount_amount,
                "vat": 0,
                "ghi_chu": "",
                "is_km": i.is_free_item
            }
            san_pham.append(item)

        request_payload = {
            "orgid": dms_client.orgid,
            "id_dms": id_dms,
            "ma_don": ma_don,
            "ck_don": ck_don,
            "kho_hang": kho_hang,
            "san_pham": san_pham
        }

        # Ghi log request
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi dữ liệu qua API DMS
        response, success = dms_client.request(
            endpoint="/PublicAPI/sync_postWarehouse",
            method="POST",
            body=request_payload
        )

        if response.get("status"):
            create_dms_log(
                status="Success",
                response_data=response,
                message="PXK create successfully."
            )
            return {"message": "PXK create successfully."}
        else:
            create_dms_log(
                status="Failed",
                response_data=response,
                message="Failed to create PXK."
            )
            frappe.logger().error(f"Failed to create: {response}")
            return {"error": response}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while create PXK.",
            rollback=True
        )
        frappe.logger().error(f"Sync Error: {str(e)}")
        return {"error": str(e)}