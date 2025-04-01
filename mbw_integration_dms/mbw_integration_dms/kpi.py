# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe

from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME
from frappe.utils import nowdate

enable_dms = check_enable_integration_dms()

def get_kpi_dms(**kwargs):
    if enable_dms:
        try:
            dms_client = DMSApiClient()
            month = int(nowdate().split('-')[1])
            year = int(nowdate().split('-')[0])

            # Dữ liệu gửi đi
            request_payload = {
                "orgid": dms_client.orgid,
                "month": month,
                "year": year
            }

            # Ghi log request
            create_dms_log(
                status="Processing",
                method="POST",
                message="Sync KPI DMS",
                request_data=request_payload
            )

            # Gửi dữ liệu qua API DMS
            response, success = dms_client.request(
                endpoint="/PublicAPI/reportKPI",
                method="POST",
                body=request_payload
            )

            if response.get("result"):
                results = response.get("result")

                for i in results:
                    existing_kpi = frappe.db.exists(
                    "DMS KPI", 
                    {"month": month, "year": year, "ten_nhan_vien": i["name"]}
                )

                data = {
                    "doctype": "DMS KPI",
                    "naming_series": "KPI-.MM.-.YYYY.-",
                    "ten_nhom": i.get("ten_nhom"),
                    "ma_nhom": i.get("ma_nhom"),
                    "parent_id": i.get("parentID"),
                    "email": i.get("email"),
                    "ma_nhan_vien": i.get("code"),
                    "ten_nhan_vien": i.get("name"),
                    "left_day": i.get("leftday") or 0,
                    
                    # Dữ liệu từ KH
                    "doanh_so": i["KH"].get("doanh_so", 0),
                    "doanh_thu": i["KH"].get("doanh_thu", 0),
                    "san_luong": i["KH"].get("san_luong", 0),
                    "so_don_hang": i["KH"].get("so_don_hang", 0),
                    "so_khach_hang_vieng_tham": i["KH"].get("so_kh_vieng_tham", 0),
                    "so_khach_hang_dat_hang": i["KH"].get("so_kh_dat_hang", 0),
                    "so_khach_hang_moi": i["KH"].get("so_kh_moi", 0),
                    "sku": i["KH"].get("sku", 0),
                    "gio": i["KH"].get("gio", 0),
                    
                    # Dữ liệu nhóm & sản phẩm trọng tâm
                    "group_id": i["KH"]["group"].get("groupID"),
                    "name_group": i["KH"]["group"].get("name"),
                    "san_pham_trong_tam": ", ".join([sp["tsp"] for sp in i["KH"]["sp_trong_tam"].get("san_pham", []) if isinstance(sp, dict) and "tsp" in sp]) if isinstance(i["KH"]["sp_trong_tam"].get("san_pham"), list) else "",
                    "tong_don_hang": i["KH"]["sp_trong_tam"].get("tong_dh", 0),
                    "tong_khach_hang": i["KH"]["sp_trong_tam"].get("tong_kh", 0),
                    "tong_so_luong": i["KH"]["sp_trong_tam"].get("tong_sl", 0),
                    "tong_so_tien": i["KH"]["sp_trong_tam"].get("tong_st", 0),

                    # Dữ liệu từ TH
                    "doanh_so_th": i["TH"].get("doanh_so", 0),
                    "doanh_thu_th": i["TH"].get("doanh_thu", 0),
                    "san_luong_th": i["TH"].get("san_luong", 0),
                    "so_don_hang_th": i["TH"].get("so_don_hang", 0),
                    "so_khach_hang_vieng_tham_th": i["TH"].get("so_kh_vieng_tham", 0),
                    "so_khach_hang_moi_th": i["TH"].get("so_kh_moi", 0),
                    "sku_th": i["TH"].get("sku", 0),
                    "gio_th": i["TH"].get("gio", 0),
                    
                    # Các chỉ số VT
                    "vt_co_don_hang_trong_tuyen": i["TH"].get("vt_co_dh_tt", 0),
                    "vt_khong_don_hang_trong_tuyen": i["TH"].get("vt_khong_dh_tt", 0),
                    "vt_co_don_hang_ngoai_tuyen": i["TH"].get("vt_co_dh_nt", 0),
                    "vt_khong_don_hang_ngoai_tuyen": i["TH"].get("vt_khong_dh_nt", 0),
                    "khach_hang_vt_duy_nhat": i["TH"].get("kh_vt_unique", 0),
                    "sku0": i["TH"].get("sku0", 0),
                    "so_khach_hang_dat_hang_th": i["TH"].get("so_kh_dat_hang", 0),

                    "month": month,
                    "year": year,
                }

                if existing_kpi:
                    # Nếu đã tồn tại, cập nhật bản ghi
                    data.pop("doctype", None)  # Loại bỏ doctype nếu tồn tại
                    frappe.db.set_value("DMS KPI", existing_kpi, data)
                else:
                    # Nếu chưa tồn tại, tạo mới bản ghi
                    new_kpi = frappe.get_doc(data)
                    new_kpi.insert(ignore_permissions=True)

                frappe.db.commit()

                create_dms_log(
                    status="Success",
                    response_data=response,
                    message="KPI synced successfully."
                )
                publish(KEY_REALTIME["key_realtime_kpi"], "KPI synced successfully.", done=True)
                return {"message": "KPI synced successfully."}
            
            else:
                create_dms_log(
                    status="Failed",
                    response_data=response,
                    message="Failed to sync KPI DMS."
                )
                frappe.logger().error(f"Failed to sync: {response}")
                publish(KEY_REALTIME["key_realtime_kpi"], f"Failed to sync: {response}", error=True)
                return {"error": response}

        except Exception as e:
            create_dms_log(
                status="Error",
                exception=str(e),
                message="Exception occurred while syncing KPI.",
                rollback=True
            )
            frappe.logger().error(f"Sync Error: {str(e)}")
            return {"error": str(e)}