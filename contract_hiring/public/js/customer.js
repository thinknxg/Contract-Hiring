frappe.ui.form.on("Customer", {
    refresh(frm) {
        if (!frm.is_new()) frm.add_custom_button("Contract Hiring Quotations",()=>frappe.set_route("List","Contract Hiring Quotation",{customer:frm.doc.name}),"Contract Hiring");
    }
});
