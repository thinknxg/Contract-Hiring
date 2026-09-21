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
