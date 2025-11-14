# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient


def create_sales_dms(doc, method):
    try:
        dms_client = DMSApiClient()

        request_payload = {
            "email": doc.email,
            "name": doc.sales_person_name,
            "code": doc.employee
        }

        # Ghi log request từng channel
        create_dms_log(
            status="Processing",
            method="POST",
            request_data=request_payload
        )

        # Gửi từng Channel
        response, success = dms_client.request(
            endpoint="/OpenAPI/V1/Sale",
            method="POST",
            body=request_payload
        )

        message = f"Sales Person create done. Response: {response}"
        status = "Success" if success else "Not Success"

        create_dms_log(
            status=status,
            message=message
        )

        return {"message": message}

    except Exception as e:
        create_dms_log(
            status="Error",
            exception=str(e),
            message="Exception occurred while creating Sales Person in DMS.",
            rollback=True
        )