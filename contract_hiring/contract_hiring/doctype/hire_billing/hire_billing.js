frappe.ui.form.on("Hire Billing", {
    refresh(frm) {
        if (frm.doc.docstatus === 0 && frm.doc.sales_order) {
            frm.add_custom_button("Recalculate Items", () => {
                frappe.call({method: "contract_hiring.contract_hiring.doctype.hire_billing.hire_billing.get_billing_items",
                    args: {hire_order: frm.doc.sales_order, from_date: frm.doc.from_date, to_date: frm.doc.to_date}, freeze: true,
                    callback: r => {
                        frm.clear_table("items");
                        (r.message.items || []).forEach(it => frm.add_child("items", it));
                        frm.refresh_field("items");
                        if ((r.message.notes || []).length) frappe.msgprint(r.message.notes.join("<br>"));
                        frm.dirty();
                    }});
            });
        }
        if (frm.doc.sales_invoice) frm.add_custom_button("Open Sales Invoice",()=>frappe.set_route("Form","Sales Invoice",frm.doc.sales_invoice),"Navigate");
        if (frm.doc.sales_order) frm.add_custom_button("Open Sales Order",()=>frappe.set_route("Form","Sales Order",frm.doc.sales_order),"Navigate");
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
