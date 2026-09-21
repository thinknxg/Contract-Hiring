frappe.ui.form.on("Hire Delivery", {
    refresh(frm) {
        if (frm.doc.stock_entry) frm.add_custom_button("Open Stock Entry",()=>frappe.set_route("Form","Stock Entry",frm.doc.stock_entry),"Navigate");
        if (frm.doc.sales_order) frm.add_custom_button("Open Sales Order",()=>frappe.set_route("Form","Sales Order",frm.doc.sales_order),"Navigate");
    }
});
