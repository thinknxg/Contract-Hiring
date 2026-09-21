frappe.ui.form.on("Customer", {
    refresh(frm) {
        if (!frm.is_new()) frm.add_custom_button("Hiring Sales Orders",()=>frappe.set_route("List","Sales Order",{customer:frm.doc.name,hiring_type:["!=",""]}),"Contract Hiring");
    }
});
