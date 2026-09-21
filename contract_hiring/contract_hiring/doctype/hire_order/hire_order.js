frappe.ui.form.on("Hire Order", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            const make = (label, method, doctype) => frm.add_custom_button(label, () => {
                frappe.call({method, args:{hire_order:frm.doc.name}, freeze:true,
                    callback:r => {if(r.message) frappe.set_route("Form",doctype,r.message);}});
            });
            make("Create Hire Delivery","contract_hiring.contract_hiring.doctype.hire_delivery.hire_delivery.make_delivery","Hire Delivery");
            if (frm.doc.hiring_type !== "Material Sale") make("Create Hire Return","contract_hiring.contract_hiring.doctype.hire_return.hire_return.make_return","Hire Return");
            if (frm.doc.hiring_type === "Contract Hire") make("Create Service Delivery","contract_hiring.contract_hiring.doctype.service_delivery.service_delivery.make_service_delivery","Service Delivery");
            make("Create Hire Billing","contract_hiring.contract_hiring.doctype.hire_billing.hire_billing.make_billing","Hire Billing");
        }
        if (frm.doc.quotation) {
            frm.add_custom_button("Open Quotation",()=>frappe.set_route("Form","Contract Hiring Quotation",frm.doc.quotation),"Navigate");
        }
    }
});
