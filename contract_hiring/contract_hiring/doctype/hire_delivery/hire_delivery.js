frappe.ui.form.on("Hire Delivery", {
    refresh(frm) {
        if (frm.doc.stock_entry) frm.add_custom_button("Open Stock Entry",()=>frappe.set_route("Form","Stock Entry",frm.doc.stock_entry),"Navigate");
        if (frm.doc.hire_order) frm.add_custom_button("Open Hire Order",()=>frappe.set_route("Form","Hire Order",frm.doc.hire_order),"Navigate");
    }
});
