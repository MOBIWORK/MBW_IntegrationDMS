frappe.ui.form.on("Sales Invoice", {
    onload: function(frm) {
        if (frm.is_new() && frm.doc.items.length > 0 && frm.doc.items[0].sales_order) {
            // Kiểm tra xem có sản phẩm khuyến mại không
            let has_free_item = frm.doc.items.some(item => item.is_free_item);

            if (!has_free_item) {
                return;
            }

            frappe.call({
                method: "mbw_integration_dms.mbw_integration_dms.sales_invoice.get_remaining_qty",
                args: {
                    sales_order: frm.doc.items[0].sales_order
                },
                callback: function(response) {
                    if (response.message && response.message.length > 0) {
                        frm.clear_table("items");
                        response.message.forEach(item => {
                            let row = frm.add_child("items");
                            row.item_code = item.item_code;
                            row.item_name = item.item_name;
                            row.stock_uom = item.stock_uom;
                            row.sales_order = item.sales_order;
                            row.uom = item.uom;
                            row.qty = item.remaining_qty;
                            row.rate = item.rate;
                            row.is_free_item = item.is_free_item;
                            row.income_account = item.income_account;
                        });
                        frm.refresh_field("items");
                    }
                }
            });
        }
    }
});
