function ch_row_qty(frm, cdt, cdn) {
    const r = locals[cdt][cdn];
    const loc = flt(r.locations) || 1;
    let qty = null;
    if (r.rate_type === "M3") qty = flt(r.length) * flt(r.breadth) * flt(r.height) * loc;
    else if (r.rate_type === "SQM") qty = flt(r.length) * flt(r.breadth) * loc;
    else if (r.rate_type === "Lumpsum") qty = 1;
    if (qty !== null && flt(r.qty) !== qty) frappe.model.set_value(cdt, cdn, "qty", qty);
}

frappe.ui.form.on("Sales Order Item", {
    length: ch_row_qty, breadth: ch_row_qty, height: ch_row_qty, locations: ch_row_qty, rate_type: ch_row_qty
});

const CH = "contract_hiring.contract_hiring.doctype.";

function ch_make(doctype, method, args) {
    frappe.call({ method: CH + method, args: args, freeze: true }).then((r) => {
        if (r.message) frappe.set_route("Form", doctype, r.message);
    });
}

frappe.ui.form.on("Sales Order", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1 || !frm.doc.hiring_type) return;
        const so = frm.doc.name;
        const t = frm.doc.hiring_type;

        frm.add_custom_button("Hire Delivery", () =>
            ch_make("Hire Delivery", "hire_delivery.hire_delivery.make_delivery", { sales_order: so }), "Hire");

        if (t === "Contract Hire") {
            frm.add_custom_button("Service Delivery", () =>
                ch_make("Service Delivery", "service_delivery.service_delivery.make_service_delivery", { sales_order: so }), "Hire");
        }

        if (t !== "Material Sale") {
            frm.add_custom_button("Hire Return", () =>
                ch_make("Hire Return", "hire_return.hire_return.make_return", { sales_order: so }), "Hire");
        }

        frm.add_custom_button("Hire Billing", () => {
            frappe.prompt([
                { fieldname: "from_date", label: "From Date (blank = first delivery / service)", fieldtype: "Date" },
                { fieldname: "to_date", label: "To Date", fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() }
            ], (v) => ch_make("Hire Billing", "hire_billing.hire_billing.make_billing",
                { sales_order: so, from_date: v.from_date || "", to_date: v.to_date }),
            "Hire Billing period", "Create");
        }, "Hire");
    }
});
