import frappe
from frappe.model.document import Document
from frappe.utils import flt

def delivered_for(ho, item):
    return flt(frappe.db.sql("""
        select sum(di.qty) from `tabHire Delivery Item` di
        join `tabHire Delivery` d on d.name = di.parent
        where d.hire_order = %s and di.item = %s and d.docstatus = 1
    """, (ho, item))[0][0])

def returned_for(ho, item):
    return flt(frappe.db.sql("""
        select sum(ri.qty_to_return) from `tabHire Return Item` ri
        join `tabHire Return` r on r.name = ri.parent
        where r.hire_order = %s and ri.item = %s and r.docstatus = 1
    """, (ho, item))[0][0])

def returned_breakdown(ho, item):
    row = frappe.db.sql("""
        select sum(ri.qty_to_return), sum(ri.damage_qty), sum(ri.scrap_qty), sum(ri.lost_qty)
        from `tabHire Return Item` ri
        join `tabHire Return` r on r.name = ri.parent
        where r.hire_order = %s and ri.item = %s and r.docstatus = 1
    """, (ho, item))[0]
    return [flt(x) for x in row]

def refresh_counters(ho):
    for r in frappe.get_all("Hire Order Item", filters={"parent": ho}, fields=["name", "item"]):
        delivered = delivered_for(ho, r.item)
        returned, damage, scrap, lost = returned_breakdown(ho, r.item)
        frappe.db.set_value("Hire Order Item", r.name, {
            "delivered_qty": delivered,
            "returned_qty": returned,
            "damage_qty": damage,
            "scrap_qty": scrap,
            "lost_qty": lost,
            "balance_qty": max(delivered - returned, 0),
        }, update_modified=False)
    update_status(ho)

def update_status(ho_name):
    docstatus = frappe.db.get_value("Hire Order", ho_name, "docstatus")
    if docstatus == 2:
        status = "Cancelled"
    elif docstatus == 0:
        status = "Draft"
    else:
        ordered = {}
        for r in frappe.get_all("Hire Order Item", filters={"parent": ho_name}, fields=["item", "qty"]):
            if frappe.db.get_value("Item", r.item, "is_stock_item"):
                ordered[r.item] = ordered.get(r.item, 0) + flt(r.qty)
        delivered = {i: delivered_for(ho_name, i) for i in ordered}
        returned = {i: returned_for(ho_name, i) for i in ordered}
        eps = 0.000001
        if not any(v > eps for v in delivered.values()):
            status = "Confirmed"
        elif not all(delivered[i] >= ordered[i] - eps for i in ordered):
            status = "Partially Delivered"
        elif not any(v > eps for v in returned.values()):
            status = "Delivered"
        elif not all(returned[i] >= delivered[i] - eps for i in ordered):
            status = "Partially Returned"
        else:
            status = "Closed"
    frappe.db.set_value("Hire Order", ho_name, "status", status, update_modified=False)

class HireOrder(Document):
    def validate(self):
        if not self.quotation:
            frappe.throw("A Hire Order is created from a submitted quotation. Use Create Hire Order on the quotation.")
        if frappe.db.get_value("Contract Hiring Quotation", self.quotation, "docstatus") != 1:
            frappe.throw(f"Quotation {self.quotation} must be submitted first.")
        seen = set()
        for r in self.items:
            if r.item in seen:
                frappe.throw(f"Row {r.idx}: {r.item} is already on this order. Combine it into one row.")
            seen.add(r.item)
        total_qty=total=0
        for r in self.items:
            r.calculated_volume=flt(r.length)*flt(r.breadth)*flt(r.height)*(flt(r.locations) or 1)
            if r.rate_type=="M3": base=r.calculated_volume
            elif r.rate_type=="SQM": base=flt(r.length)*flt(r.breadth)*(flt(r.locations) or 1)
            elif r.rate_type=="Lumpsum": base=1
            else: base=flt(r.qty)
            r.amount=base*flt(r.rate)*(flt(r.duration) or 1)
            r.ordered_qty=flt(r.qty)
            r.delivered_qty=delivered_for(self.name,r.item) if self.name else 0
            r.returned_qty=returned_for(self.name,r.item) if self.name else 0
            r.balance_qty=max(flt(r.delivered_qty)-flt(r.returned_qty),0)
            total_qty += flt(r.qty); total += flt(r.amount)
        self.total_ordered_qty=total_qty; self.total_ordered_amount=total
        if self.docstatus==0: self.status="Draft"

    def on_submit(self):
        update_status(self.name)

    def on_cancel(self):
        update_status(self.name)

@frappe.whitelist()
def get_deliverable_items(hire_order):
    ho=frappe.get_doc("Hire Order",hire_order)
    out=[]
    for r in ho.items:
        delivered=delivered_for(ho.name,r.item)
        out.append({"item":r.item,"description":r.description,"ordered_qty":flt(r.qty),"delivered_qty":delivered,
                    "balance_qty":max(flt(r.qty)-delivered,0),"uom":r.uom})
    return out

@frappe.whitelist()
def get_returnable_items(hire_order):
    ho=frappe.get_doc("Hire Order",hire_order)
    out=[]
    for r in ho.items:
        delivered=delivered_for(ho.name,r.item)
        returned=returned_for(ho.name,r.item)
        out.append({"item":r.item,"description":r.description,"delivered_qty":delivered,
                    "returned_qty":returned,"balance_qty":max(delivered-returned,0),"uom":r.uom})
    return out
