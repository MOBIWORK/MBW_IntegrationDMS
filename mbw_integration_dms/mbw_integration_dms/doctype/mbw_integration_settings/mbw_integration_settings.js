// Copyright (c) 2025, MBW and contributors
// For license information, please see license.txt

frappe.ui.form.on("MBW Integration Settings", {
	refresh(frm) {

	},
    auto_add_category: function (frm) {
        frappe.prompt(
            [
                {
                    fieldname: 'confirmation',
                    fieldtype: 'HTML',
                    options: '<p>Dữ liệu hiện tại của các Doctype: </p>' +
                        '<p>Brand, Industry Type, UOM, ' +
                        'Customer Type, DMS Customer Group, Territory, Channel, Warehouse, Supplier</p>' +
                        '<p>Sẽ bị <b>Thay Thế</b> bởi dữ liệu mẫu theo tiêu chuẩn phân phối Việt Nam. </p>' +
						'<p>Bạn có muốn tiếp tục thực hiện?</p>'
                }
            ],
            (values) => {
				//Action when select apply
                frappe.call({
                    method: 'mbw_integration_dms.api.auto_add_category.auto_add_category',
                    callback: function (r) {
                        if (!r.exc) {
                            frappe.msgprint('Dữ liệu đã bị thay thế.');
                        }
                    }
                });
            },
            'Xác nhận hành động',
            'Apply'
        );
    }
});
