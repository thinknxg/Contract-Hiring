frappe.ui.form.on("Hire Return", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && !frm.doc.direct_invoice && (frm.doc.items || []).some(r => flt(r.damage_qty) + flt(r.scrap_qty) + flt(r.lost_qty) > 0)) {
            frm.add_custom_button("Create Direct Invoice", () => {
                frappe.call({method: "contract_hiring.contract_hiring.doctype.hire_return.hire_return.make_direct_invoice",
                    args: {hire_return: frm.doc.name}, freeze: true,
                    callback: r => { if (r.message) frappe.set_route("Form", "Sales Invoice", r.message); }});
            }, "Create");
        }
        if (frm.doc.direct_invoice) frm.add_custom_button("Open Direct Invoice", () => frappe.set_route("Form", "Sales Invoice", frm.doc.direct_invoice), "Navigate");
        if (frm.doc.stock_entry) frm.add_custom_button("Open Stock Entry",()=>frappe.set_route("Form","Stock Entry",frm.doc.stock_entry),"Navigate");
        if (frm.doc.sales_order) frm.add_custom_button("Open Sales Order",()=>frappe.set_route("Form","Sales Order",frm.doc.sales_order),"Navigate");
    }
});
