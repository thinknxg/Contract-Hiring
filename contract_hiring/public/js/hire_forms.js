(function () {
    if (frappe.ch_hire_forms) return;
    frappe.ch_hire_forms = true;

    const METHOD = "contract_hiring.contract_hiring.doctype.hire_return.hire_return.make_direct_invoice";
    const has_loss = (frm) => (frm.doc.items || []).some(r => flt(r.damage_qty) + flt(r.scrap_qty) + flt(r.lost_qty) > 0);

    ["Hire Delivery", "Service Delivery", "Hire Return", "Hire Billing"].forEach((dt) => {
        frappe.ui.form.on(dt, {
            refresh(frm) {
                if (frm.is_new() || !frm.doc.sales_order) return;
                frm.add_custom_button("Back to Sales Order", () => frappe.set_route("Form", "Sales Order", frm.doc.sales_order));
            },
            on_submit(frm) {
                if (frm.doctype === "Hire Return" && has_loss(frm)) {
                    frappe.show_alert({ message: "Now click Create Direct Invoice to bill the damage / scrap / lost items.", indicator: "orange" }, 8);
                    return;
                }
                if (frm.doc.sales_order) {
                    setTimeout(() => frappe.set_route("Form", "Sales Order", frm.doc.sales_order), 800);
                }
            }
        });
    });

    frappe.ui.form.on("Hire Return", {
        refresh(frm) {
            if (frm.doc.docstatus !== 1) return;
            if (frm.doc.direct_invoice) {
                frm.add_custom_button("Open Direct Invoice", () => frappe.set_route("Form", "Sales Invoice", frm.doc.direct_invoice));
            } else if (has_loss(frm)) {
                frm.add_custom_button("Create Direct Invoice", () => {
                    frappe.call({ method: METHOD, args: { hire_return: frm.doc.name }, freeze: true }).then((r) => {
                        if (r.message) frappe.set_route("Form", "Sales Invoice", r.message);
                    });
                }).removeClass("btn-default").addClass("btn-primary");
            }
        }
    });
})();
