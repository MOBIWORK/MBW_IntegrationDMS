# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

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
		self, url: Optional[str] = None, access_token: Optional[str] = None
	):  
        company = frappe.defaults.get_user_default("company")
        self.settings = frappe.get_doc(SETTING_DOCTYPE, {"name": company})
        self.base_url = self.settings.dms_api_url or f"http://apierpnext.mobiwork.vn"
        self.access_token = self.settings.dms_access_token
        self.orgid = self.settings.orgid
        self.__initialize_auth()

    def __initialize_auth(self):
        """Initialize and setup authentication details"""
        
        self._auth_headers = {
            "Content-Type": "application/json",
            "tokenkey": self.access_token,
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
				method=method, url=url, headers=headers, json=body, params=params, files=files
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