frappe.ui.form.on("Hire Billing", {
    refresh(frm) {
        if (frm.doc.sales_invoice) frm.add_custom_button("Open Sales Invoice",()=>frappe.set_route("Form","Sales Invoice",frm.doc.sales_invoice),"Navigate");
        if (frm.doc.hire_order) frm.add_custom_button("Open Hire Order",()=>frappe.set_route("Form","Hire Order",frm.doc.hire_order),"Navigate");
    }
});
frappe.ui.form.on("Hire Billing Item", {
    qty(frm,cdt,cdn){recalc(frm,cdt,cdn);},
    rate(frm,cdt,cdn){recalc(frm,cdt,cdn);},
    duration(frm,cdt,cdn){recalc(frm,cdt,cdn);}
});
function recalc(frm,cdt,cdn){
    const r=locals[cdt][cdn];
    r.amount=flt(r.qty)*flt(r.rate)*(flt(r.duration)||1);
    frm.refresh_field("items");
}
