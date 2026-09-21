frappe.ui.form.on("Service Delivery", {
    refresh(frm) {
        if (frm.doc.sales_order) frm.add_custom_button("Open Sales Order", () => frappe.set_route("Form", "Sales Order", frm.doc.sales_order), "Navigate");
    }
});
