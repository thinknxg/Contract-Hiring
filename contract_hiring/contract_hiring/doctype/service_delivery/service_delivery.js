frappe.ui.form.on("Service Delivery", {
    refresh(frm) {
        if (frm.doc.hire_order) frm.add_custom_button("Open Hire Order", () => frappe.set_route("Form", "Hire Order", frm.doc.hire_order), "Navigate");
    }
});
