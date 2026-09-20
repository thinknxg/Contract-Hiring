import frappe
from frappe.model.document import Document
from frappe.utils import flt

from contract_hiring.contract_hiring.doctype.hire_order.hire_order import (
    delivered_for,
    get_returnable_items,
    refresh_counters,
    returned_for,
)

class HireReturn(Document):
    def validate(self):
        ho = frappe.get_doc("Hire Order", self.hire_order)
        if ho.docstatus != 1:
            frappe.throw(f"Hire Order {ho.name} must be submitted before creating a return.")
        self.customer, self.project, self.site = ho.customer, ho.project, ho.site
        if not self.source_warehouse:
            self.source_warehouse = frappe.db.get_value("Project Site", self.site, "warehouse")
        if not self.target_warehouse:
            self.target_warehouse = frappe.get_single("Contract Hiring Settings").main_stock_warehouse
        self.validate_quantities()

    def validate_quantities(self):
        per_item = {}
        for r in self.items:
            accounted = flt(r.normal_return_qty) + flt(r.damage_qty) + flt(r.scrap_qty) + flt(r.lost_qty)
            expected = flt(r.qty_to_return)
            if accounted < expected - 0.000001:
                frappe.throw(
                    f"Row {r.idx}: Normal + Damage + Scrap + Lost ({accounted}) is less than Qty to Return ({expected}). "
                    "Reduce Qty to Return to what actually came back; the rest stays on hire."
                )
            r.excess_qty = max(accounted - expected, 0)
            if flt(r.excess_qty) > flt(r.normal_return_qty) + 0.000001:
                frappe.throw(f"Row {r.idx}: Excess ({r.excess_qty}) cannot be more than the normal return quantity.")
            per_item[r.item] = per_item.get(r.item, 0) + flt(r.qty_to_return)
        for item, qty in per_item.items():
            on_hire = delivered_for(self.hire_order, item) - returned_for(self.hire_order, item)
            if qty > on_hire + 0.000001:
                frappe.throw(f"{item}: returning {qty} but only {on_hire} is on hire.")

    def on_submit(self):
        self.stock_entry = create_return_stock_entry(self)
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
def make_return(hire_order):
    ho = frappe.get_doc("Hire Order", hire_order)
    if ho.docstatus != 1:
        frappe.throw("Submit the Hire Order first.")
    rows = [x for x in get_returnable_items(ho.name) if x["balance_qty"] > 0]
    if not rows:
        frappe.throw("Nothing left to return against this order.")
    r = frappe.new_doc("Hire Return")
    r.hire_order = ho.name; r.customer = ho.customer; r.project = ho.project; r.site = ho.site
    r.source_warehouse = frappe.db.get_value("Project Site", ho.site, "warehouse")
    r.target_warehouse = frappe.get_single("Contract Hiring Settings").main_stock_warehouse
    for x in rows:
        r.append("items", {"item": x["item"], "description": x["description"], "delivered_qty": x["delivered_qty"],
                           "previously_returned": x["returned_qty"], "qty_to_return": x["balance_qty"],
                           "normal_return_qty": x["balance_qty"], "uom": x["uom"]})
    r.insert()
    return r.name

def create_return_stock_entry(doc):
    settings = frappe.get_single("Contract Hiring Settings")
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer"
    se.company = frappe.db.get_value("Project", doc.project, "company") or frappe.defaults.get_global_default("company")
    se.posting_date = doc.return_date
    for r in doc.items:
        uom = r.uom or frappe.db.get_value("Item", r.item, "stock_uom")
        normal = flt(r.normal_return_qty) - flt(r.excess_qty)
        if normal:
            se.append("items", {"item_code": r.item, "qty": normal, "uom": uom, "s_warehouse": doc.source_warehouse,
                                "t_warehouse": doc.target_warehouse, "description": r.description})
        for label, qty, wh in [("Damage", flt(r.damage_qty), settings.damage_warehouse),
                               ("Scrap", flt(r.scrap_qty), settings.scrap_warehouse),
                               ("Lost", flt(r.lost_qty), settings.lost_warehouse)]:
            if not qty:
                continue
            if not wh:
                frappe.throw(f"Set the {label} Warehouse in Contract Hiring Settings.")
            se.append("items", {"item_code": r.item, "qty": qty, "uom": uom, "s_warehouse": doc.source_warehouse,
                                "t_warehouse": wh, "description": r.description})
    if not se.items:
        frappe.throw("Enter at least one return classification.")
    se.insert(ignore_permissions=True); se.submit()
    return se.name
