import frappe
from frappe.utils import flt

RATE_TYPES = {
    "Material Hire": ("Day", "Month"),
    "Contract Hire": ("M3", "SQM", "Nos", "Day", "Month", "Lumpsum"),
}


def dimension_qty(r):
    loc = flt(r.get("locations")) or 1
    rt = r.get("rate_type")
    if rt == "M3":
        return flt(r.get("length")) * flt(r.get("breadth")) * flt(r.get("height")) * loc
    if rt == "SQM":
        return flt(r.get("length")) * flt(r.get("breadth")) * loc
    if rt == "Lumpsum":
        return 1
    return None


def apply_rules(doc, method=None):
    """Runs before validate on Quotation and Sales Order. Documents without a hiring type are left alone;
    Material Sale is plain ERPNext."""
    htype = doc.get("hiring_type")
    if htype not in RATE_TYPES:
        return
    allowed = RATE_TYPES[htype]
    seen = set()
    for r in doc.items:
        rt = r.get("rate_type")
        if rt not in allowed:
            frappe.throw(f"Row {r.idx}: Rate Type {rt or '(blank)'} is not allowed on a {htype} {doc.doctype}. Allowed: {', '.join(allowed)}.")
        qty = dimension_qty(r)
        if qty is not None:
            r.qty = qty
        if rt == "M3" and not r.get("period"):
            frappe.throw(f"Row {r.idx}: choose a Period (Day, Month or Year) for an M3 line.")
        if rt not in ("M3", "SQM"):
            if r.item_code in seen:
                frappe.throw(f"Row {r.idx}: {r.item_code} is already on this {doc.doctype}. Combine it into one row.")
            seen.add(r.item_code)
    if doc.doctype == "Sales Order" and not any(i.get("prevdoc_docname") for i in doc.items):
        frappe.throw("A hiring Sales Order is created from a submitted quotation (Create > Sales Order on the Quotation).")
