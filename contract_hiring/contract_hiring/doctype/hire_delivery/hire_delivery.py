import frappe
from frappe.model.document import Document
from frappe.utils import flt

from contract_hiring.contract_hiring.doctype.hire_order.hire_order import (
    delivered_for,
    get_deliverable_items,
    refresh_counters,
)

class HireDelivery(Document):
    def validate(self):
        ho = frappe.get_doc("Hire Order", self.hire_order)
        if ho.docstatus != 1:
            frappe.throw(f"Hire Order {ho.name} must be submitted before creating a delivery.")
        self.customer, self.project, self.site = ho.customer, ho.project, ho.site
        if not self.target_warehouse:
            self.target_warehouse = frappe.db.get_value("Project Site", self.site, "warehouse")
        if not self.source_warehouse:
            self.source_warehouse = frappe.get_single("Contract Hiring Settings").main_stock_warehouse
        self.validate_quantities()

    def validate_quantities(self):
        per_item = {}
        for r in self.items:
            per_item[r.item] = per_item.get(r.item, 0) + flt(r.qty)
        for item, qty in per_item.items():
            ordered = flt(frappe.db.sql(
                "select sum(qty) from `tabHire Order Item` where parent = %s and item = %s",
                (self.hire_order, item))[0][0])
            already = delivered_for(self.hire_order, item)
            if qty + already > ordered + 0.000001:
                frappe.throw(f"{item}: delivering {qty} on top of {already} already delivered exceeds the ordered {ordered}.")

    def on_submit(self):
        self.stock_entry = create_stock_entry(self)
        self.db_set("stock_entry", self.stock_entry)
        refresh_counters(self.hire_order)

    def on_cancel(self):
        if self.stock_entry:
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.flags.ignore_permissions = True
                se.cancel()
        refresh_counters(self.hire_order)

@frappe.whitelist()
def make_delivery(hire_order):
    ho = frappe.get_doc("Hire Order", hire_order)
    if ho.docstatus != 1:
        frappe.throw("Submit the Hire Order first.")
    d = frappe.new_doc("Hire Delivery")
    d.hire_order = ho.name; d.customer = ho.customer; d.project = ho.project; d.site = ho.site
    d.target_warehouse = frappe.db.get_value("Project Site", ho.site, "warehouse")
    d.source_warehouse = frappe.get_single("Contract Hiring Settings").main_stock_warehouse
    for r in get_deliverable_items(ho.name):
        if r["balance_qty"] > 0:
            d.append("items", {"item": r["item"], "description": r["description"], "qty": r["balance_qty"], "uom": r["uom"]})
    if not d.items:
        frappe.throw("Nothing left to deliver against this order.")
    d.insert()
    return d.name

def create_stock_entry(doc):
    if not doc.source_warehouse or not doc.target_warehouse:
        frappe.throw("Set both Source Warehouse and Site Warehouse.")
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer"
    se.company = frappe.db.get_value("Project", doc.project, "company") or frappe.defaults.get_global_default("company")
    se.posting_date = doc.delivery_date
    for r in doc.items:
        se.append("items", {"item_code": r.item, "qty": flt(r.qty), "uom": r.uom or frappe.db.get_value("Item", r.item, "stock_uom"),
                            "s_warehouse": doc.source_warehouse, "t_warehouse": doc.target_warehouse, "description": r.description})
    se.insert(ignore_permissions=True); se.submit()
    return se.name
