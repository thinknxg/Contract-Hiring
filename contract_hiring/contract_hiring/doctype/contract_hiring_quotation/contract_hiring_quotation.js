function ch_calc(r) {
    const loc = flt(r.locations) || 1;
    const vol = flt(r.length) * flt(r.breadth) * flt(r.height) * loc;
    r.calculated_volume = vol;
    let base = flt(r.qty);
    if (r.rate_type === "M3") base = vol;
    else if (r.rate_type === "SQM") base = flt(r.length) * flt(r.breadth) * loc;
    else if (r.rate_type === "Lumpsum") base = 1;
    r.amount = base * flt(r.rate) * (flt(r.duration) || 1);
}
function ch_refresh(frm) {
    (frm.doc.items || []).forEach(ch_calc);
    frm.refresh_field("items");
    let qty=0, vol=0, total=0;
    (frm.doc.items || []).forEach(r => {qty+=flt(r.qty);vol+=flt(r.calculated_volume);total+=flt(r.amount);});
    frm.set_value("total_qty",qty); frm.set_value("total_volume_m3",vol); frm.set_value("grand_total",total);
}
frappe.ui.form.on("Contract Hiring Quotation", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Create Hire Order", () => {
                frappe.call({
                    method:"contract_hiring.contract_hiring.doctype.contract_hiring_quotation.contract_hiring_quotation.create_hire_order",
                    args:{quotation:frm.doc.name}, freeze:true,
                    callback:r => { if(r.message) frappe.set_route("Form","Hire Order",r.message); }
                });
            }, "Create");
            frm.add_custom_button("Create Revision", () => {
                frm.call({
                    method:"create_revision", doc:frm.doc, freeze:true,
                    callback:r => { if(r.message) frappe.set_route("Form","Contract Hiring Quotation",r.message); }
                });
            }, "Create");
        }
    },
    validate(frm){ ch_refresh(frm); }
});
frappe.ui.form.on("Contract Hiring Quotation Item", {
    length:ch_refresh,breadth:ch_refresh,height:ch_refresh,locations:ch_refresh,
    qty:ch_refresh,rate:ch_refresh,rate_type:ch_refresh,duration:ch_refresh
});
