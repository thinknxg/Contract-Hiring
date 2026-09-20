frappe.ui.form.on("Project", {
    refresh(frm) {
        if (!frm.is_new()) frm.add_custom_button("Create Project Site",()=>frappe.new_doc("Project Site",{project:frm.doc.name}),"Contract Hiring");
    }
});
