# Copyright (c) 2025, TuanBD MBWD
# For license information, please see LICENSE

import frappe
from mbw_integration_dms.mbw_integration_dms.apiclient import DMSApiClient
from mbw_integration_dms.mbw_integration_dms.utils import create_dms_log, check_enable_integration_dms
from mbw_integration_dms.mbw_integration_dms.helpers.helpers import publish
from mbw_integration_dms.mbw_integration_dms.constants import KEY_REALTIME
from frappe.utils import nowdate

enable_dms = check_enable_integration_dms()

def prepare_kpi_data(i, month, year):
    # Chuẩn bị dữ liệu KPI cho mỗi nhân viên
    print('========================= value: ', i.get("leftday", 0), flush=True)
    data = {
        "doctype": "DMS KPI",
        "naming_series": "KPI-.MM.-.YYYY.-",
        "ten_nhom": i.get("ten_nhom"),
        "ma_nhom": i.get("ma_nhom"),
        "parent_id": i.get("parentID"),
        "email": i.get("email"),
        "ma_nhan_vien": i.get("code"),
        "ten_nhan_vien": i.get("name"),
        "left_day": i.get("leftday") if i.get("leftday") else 0,
        "month": month,
        "year": year,
    }

    # Dữ liệu từ KH
    kh_data = i.get("KH", {})
    data.update({
        "doanh_so": kh_data.get("doanh_so", 0),
        "doanh_thu": kh_data.get("doanh_thu", 0),
        "san_luong": kh_data.get("san_luong", 0),
        "so_don_hang": kh_data.get("so_don_hang", 0),
        "so_khach_hang_vieng_tham": kh_data.get("so_kh_vieng_tham", 0),
        "so_khach_hang_dat_hang": kh_data.get("so_kh_dat_hang", 0),
        "so_khach_hang_moi": kh_data.get("so_kh_moi", 0),
        "sku": kh_data.get("sku", 0),
        "gio": kh_data.get("gio", 0),
        "group_id": kh_data.get("group", {}).get("groupID"),
        "name_group": kh_data.get("group", {}).get("name"),
        "san_pham_trong_tam": ", ".join([sp["tsp"] for sp in kh_data.get("sp_trong_tam", {}).get("san_pham", []) if isinstance(sp, dict) and "tsp" in sp]),
        "tong_don_hang": kh_data.get("sp_trong_tam", {}).get("tong_dh", 0),
        "tong_khach_hang": kh_data.get("sp_trong_tam", {}).get("tong_kh", 0),
        "tong_so_luong": kh_data.get("sp_trong_tam", {}).get("tong_sl", 0),
        "tong_so_tien": kh_data.get("sp_trong_tam", {}).get("tong_st", 0),
    })

    # Dữ liệu từ TH
    th_data = i.get("TH", {})
    data.update({
        "doanh_so_th": th_data.get("doanh_so", 0),
        "doanh_thu_th": th_data.get("doanh_thu", 0),
        "san_luong_th": th_data.get("san_luong", 0),
        "so_don_hang_th": th_data.get("so_don_hang", 0),
        "so_khach_hang_vieng_tham_th": th_data.get("so_kh_vieng_tham", 0),
        "so_khach_hang_moi_th": th_data.get("so_kh_moi", 0),
        "sku_th": th_data.get("sku", 0),
        "gio_th": th_data.get("gio", 0),
        "vt_co_don_hang_trong_tuyen": th_data.get("vt_co_dh_tt", 0),
        "vt_khong_don_hang_trong_tuyen": th_data.get("vt_khong_dh_tt", 0),
        "vt_co_don_hang_ngoai_tuyen": th_data.get("vt_co_dh_nt", 0),
        "vt_khong_don_hang_ngoai_tuyen": th_data.get("vt_khong_dh_nt", 0),
        "khach_hang_vt_duy_nhat": th_data.get("kh_vt_unique", 0),
        "sku0": th_data.get("sku0", 0),
        "so_khach_hang_dat_hang_th": th_data.get("so_kh_dat_hang", 0),
    })

    return data


@frappe.whitelist(allow_guest=True)
def get_kpi_dms(**kwargs):
    if enable_dms:
        try:
            dms_client = DMSApiClient()
            month = int(nowdate().split('-')[1])
            year = int(nowdate().split('-')[0])

            # Dữ liệu gửi đi
            request_payload = {"orgid": dms_client.orgid, "month": month, "year": year}

            # Ghi log request
            create_dms_log(status="Processing", method="POST", message="Sync KPI DMS", request_data=request_payload)

            # Gửi dữ liệu qua API DMS
            response, success = dms_client.request(endpoint="/PublicAPI/reportKPI", method="POST", body=request_payload)

            if response.get("result"):
                results = response["result"]

                for i in results:
                    sp_name = i["name"]
                    existing_sp = frappe.db.exists("Sales Person", {"name": sp_name})
                    if not existing_sp:
                        continue

                    existing_kpi = frappe.db.exists("DMS KPI", {"month": month, "year": year, "ten_nhan_vien": sp_name})
                    data = prepare_kpi_data(i, month, year)

                    if existing_kpi:
                        # Cập nhật nếu đã tồn tại
                        data.pop("doctype", None)
                        frappe.db.set_value("DMS KPI", existing_kpi, data)
                    else:
                        # Tạo mới nếu chưa tồn tại
                        new_kpi = frappe.get_doc(data)
                        new_kpi.insert(ignore_permissions=True)

                frappe.db.commit()

                create_dms_log(status="Success", response_data=response, message="KPI synced successfully.")
                publish(KEY_REALTIME["key_realtime_kpi"], "KPI synced successfully.", done=True)
                return {"message": "KPI synced successfully."}

            create_dms_log(status="Failed", response_data=response, message="Failed to sync KPI DMS.")
            frappe.logger().error(f"Failed to sync: {response}")
            publish(KEY_REALTIME["key_realtime_kpi"], f"Failed to sync: {response}", error=True)
            return {"error": response}

        except Exception as e:
            create_dms_log(status="Error", exception=str(e), message="Exception occurred while syncing KPI.", rollback=True)
            frappe.logger().error(f"Sync Error: {str(e)}")
            return {"error": str(e)}