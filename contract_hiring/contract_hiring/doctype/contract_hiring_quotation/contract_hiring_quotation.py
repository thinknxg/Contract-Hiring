import frappe
from frappe.model.document import Document
from frappe.utils import flt

def calc_row(r):
    locations = flt(r.locations) or 1
    volume = flt(r.length) * flt(r.breadth) * flt(r.height) * locations
    r.calculated_volume = volume
    if r.rate_type == "M3":
        base = volume
    elif r.rate_type == "SQM":
        base = flt(r.length) * flt(r.breadth) * locations
    elif r.rate_type == "Lumpsum":
        base = 1
    else:
        base = flt(r.qty)
    r.amount = base * flt(r.rate) * (flt(r.duration) or 1)

RATE_TYPES_BY_TYPE = {
    "Material Sale": ("Nos",),
    "Material Hire": ("Day", "Month"),
    "Contract Hire": ("M3", "SQM", "Nos", "Day", "Month", "Lumpsum"),
}

class ContractHiringQuotation(Document):
    def validate(self):
        seen = set()
        for r in self.items:
            if r.item in seen:
                frappe.throw(f"Row {r.idx}: {r.item} is already on this quotation. Combine it into one row.")
            seen.add(r.item)
        htype = self.hiring_type or "Contract Hire"
        allowed = RATE_TYPES_BY_TYPE[htype]
        for r in self.items:
            if r.rate_type not in allowed:
                frappe.throw(f"Row {r.idx}: Rate Type {r.rate_type or '(blank)'} is not allowed on a {htype} quotation. Allowed: {', '.join(allowed)}.")
        total_qty = total_volume = total = 0
        for r in self.items:
            calc_row(r)
            total_qty += flt(r.qty)
            total_volume += flt(r.calculated_volume)
            total += flt(r.amount)
        self.total_qty = total_qty
        self.total_volume_m3 = total_volume
        self.grand_total = total
        self.status = "Submitted" if self.docstatus == 1 else ("Cancelled" if self.docstatus == 2 else "Draft")

    def on_submit(self):
        self.status = "Submitted"

    def on_cancel(self):
        self.status = "Cancelled"

    @frappe.whitelist()
    def create_hire_order(self):
        return create_hire_order(self.name)

    @frappe.whitelist()
    def create_revision(self):
        old = frappe.get_doc(self.doctype, self.name)
        new = frappe.copy_doc(old)
        new.name = None
        new.docstatus = 0
        new.status = "Draft"
        new.is_revision = 1
        new.previous_quotation = old.name
        new.revision_no = (old.revision_no or 0) + 1
        new.revision_date = frappe.utils.today()
        new.insert()
        return new.name

@frappe.whitelist()
def create_hire_order(quotation):
    q = frappe.get_doc("Contract Hiring Quotation", quotation)
    if q.docstatus != 1:
        frappe.throw("Submit the quotation before creating a Hire Order.")
    existing = frappe.db.exists("Hire Order", {"quotation":q.name, "docstatus":["!=",2]})
    if existing:
        return existing
    ho = frappe.new_doc("Hire Order")
    for f in ["customer","project","site","job_type","sales_person","enquiry_no","reference_no","payment_terms","hiring_type"]:
        setattr(ho, f, getattr(q, f, None))
    ho.quotation = q.name
    for r in q.items:
        ho.append("items", {
            "item":r.item,"description":r.description,"qty":r.qty,"uom":r.uom,
            "length":r.length,"breadth":r.breadth,"height":r.height,"locations":r.locations,
            "calculated_volume":r.calculated_volume,"rate_type":r.rate_type,"rate":r.rate,
            "duration":r.duration,"period":r.period,"amount":r.amount,"ordered_qty":r.qty
        })
    ho.insert()
    q.db_set("status","Ordered")
    return ho.name
