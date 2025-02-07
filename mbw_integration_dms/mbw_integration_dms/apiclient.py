from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe import _
from frappe.utils import cstr

from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log

from mbw_integration_dms.mbw_integration_dms.constants import (
	SETTING_DOCTYPE,
)

JsonDict = Dict[str, Any]

class DMSApiClient:
    """ DMS REST API """

    def __init__(
		self, url: Optional[str] = None, access_token: Optional[str] = None,
	):
        self.settings = frappe.get_doc(SETTING_DOCTYPE)
        self.base_url = self.settings.dms_api_secret or f"http://apierpnext.mobiwork.vn/PublicAPI"
        self.access_token = self.settings.dms_password
        self.orgid = self.settings.og_name
        self.__initialize_auth()

    def __initialize_auth(self):
        """Initialize and setup authentication details"""
		
        self.access_token = self.settings.dms_password
        self._auth_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    def request(
		self,
		endpoint: str,
		method: str = "POST",
		headers: Optional[JsonDict] = None,
		body: Optional[JsonDict] = None,
		params: Optional[JsonDict] = None,
		files: Optional[JsonDict] = None,
		log_error=True,
	) -> Tuple[JsonDict, bool]:
	

        if headers is None:
            headers = {}

        headers.update(self._auth_headers)

        url = self.base_url + endpoint

        try:
            response = requests.request(
				url=url, method=method, headers=headers, json=body, params=params, files=files
			)
            response.raise_for_status()
        except Exception:
            if log_error:
                create_dms_log(status="Error", make_new=True)
            return None, False

        if method == "GET" and "application/json" not in response.headers.get("content-type"):
            return response.content, True

        data = frappe._dict(response.json())
        status = data.successful if data.successful is not None else True

        if not status:
            req = response.request
            url = f"URL: {req.url}"
            body = f"body:  {req.body.decode('utf-8')}"
            request_data = "\n\n".join([url, body])
            message = ", ".join(cstr(error["message"]) for error in data.errors)
            create_dms_log(
                status="Error", response_data=data, request_data=request_data, message=message, make_new=True
            )

        return data, status