// Copyright (c) 2025, MBW and contributors
// For license information, please see license.txt

frappe.ui.form.on("MBW Integration Log", {
	refresh(frm) {
        if (frm.doc.request_data && frm.doc.status == "Error") {
			frm.add_custom_button(__("Retry"), function () {
				frappe.call({
					method: "mbw_integration_dms.mbw_integration_dms.doctype.mbw_integration_log.mbw_integration_log.resync",
					args: {
						method: frm.doc.method,
						name: frm.doc.name,
						request_data: frm.doc.request_data,
					},
					callback: function (r) {
						frappe.msgprint(__("Reattempting to sync"));
					},
				});
			}).addClass("btn-primary");
		}
	},
});
