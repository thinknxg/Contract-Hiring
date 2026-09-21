import frappe
from frappe.model.document import Document
from frappe.utils import flt

from contract_hiring.hiring_flow import delivered_for, get_returnable_items, refresh_counters, returned_for


class HireReturn(Document):
    def validate(self):
        so = frappe.get_doc("Sales Order", self.sales_order)
        if so.docstatus != 1:
            frappe.throw(f"Sales Order {so.name} must be submitted before creating a return.")
        if so.hiring_type == "Material Sale":
            frappe.throw("A Material Sale order has no returns.")
        self.customer, self.project, self.site = so.customer, so.project, so.hiring_site
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
            on_hire = delivered_for(self.sales_order, item) - returned_for(self.sales_order, item)
            if qty > on_hire + 0.000001:
                frappe.throw(f"{item}: returning {qty} but only {on_hire} is on hire.")

    def on_submit(self):
        self.stock_entry = create_return_stock_entry(self)
        self.db_set("stock_entry", self.stock_entry)
        refresh_counters(self.sales_order)

    def on_cancel(self):
        di = self.get("direct_invoice")
        if di:
            status = frappe.db.get_value("Sales Invoice", di, "docstatus")
            if status == 1:
                frappe.throw(f"Cancel the direct invoice {di} before cancelling this return.")
            if status == 0:
                frappe.delete_doc("Sales Invoice", di, force=1, ignore_permissions=True)
        if self.stock_entry:
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.flags.ignore_permissions = True
                se.cancel()
        refresh_counters(self.sales_order)


@frappe.whitelist()
def make_return(sales_order):
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus != 1:
        frappe.throw("Submit the Sales Order first.")
    rows = [x for x in get_returnable_items(so.name) if x["balance_qty"] > 0]
    if not rows:
        frappe.throw("Nothing left to return against this order.")
    r = frappe.new_doc("Hire Return")
    r.sales_order = so.name; r.customer = so.customer; r.project = so.project; r.site = so.hiring_site
    r.source_warehouse = frappe.db.get_value("Project Site", so.hiring_site, "warehouse")
    r.target_warehouse = frappe.get_single("Contract Hiring Settings").main_stock_warehouse
    for x in rows:
        r.append("items", {"item": x["item"], "description": x["description"], "delivered_qty": x["delivered_qty"],
                           "previously_returned": x["returned_qty"], "qty_to_return": x["balance_qty"],
                           "normal_return_qty": x["balance_qty"], "uom": x["uom"]})
    r.insert()
    return r.name


@frappe.whitelist()
def make_direct_invoice(hire_return):
    hr = frappe.get_doc("Hire Return", hire_return)
    if hr.docstatus != 1:
        frappe.throw("Submit the Hire Return first.")
    current = hr.get("direct_invoice")
    if current and frappe.db.get_value("Sales Invoice", current, "docstatus") in (0, 1):
        frappe.throw(f"Direct invoice {current} already exists for this return.")
    settings = frappe.get_single("Contract Hiring Settings")
    si = frappe.new_doc("Sales Invoice")
    si.customer = hr.customer
    si.company = frappe.db.get_value("Sales Order", hr.sales_order, "company") or settings.company or frappe.defaults.get_global_default("company")
    si.project = hr.project
    si.hiring_invoice_type = "Direct Invoice"
    si.hiring_sales_order = hr.sales_order
    si.hire_return = hr.name
    for r in hr.items:
        rate = flt(frappe.db.get_value("Item", r.item, "standard_rate")) or flt(frappe.db.get_value("Item", r.item, "valuation_rate"))
        uom = r.uom or frappe.db.get_value("Item", r.item, "stock_uom")
        for label, qty in (("Damage", r.damage_qty), ("Scrap", r.scrap_qty), ("Lost", r.lost_qty)):
            if flt(qty) > 0:
                si.append("items", {"item_code": r.item, "qty": flt(qty), "uom": uom, "rate": rate,
                                    "description": f"{label}: {r.description or r.item} (Return {hr.name})"})
    if not si.items:
        frappe.throw("This return has no damage, scrap or lost quantity to invoice.")
    if settings.income_account:
        for row in si.items:
            row.income_account = settings.income_account
    if settings.tax_template:
        from erpnext.controllers.accounts_controller import get_taxes_and_charges
        si.taxes_and_charges = settings.tax_template
        si.extend("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", settings.tax_template))
    si.insert(ignore_permissions=True)
    hr.db_set("direct_invoice", si.name)
    return si.name


def create_return_stock_entry(doc):
    settings = frappe.get_single("Contract Hiring Settings")
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Transfer"
    se.company = frappe.db.get_value("Sales Order", doc.sales_order, "company") or frappe.defaults.get_global_default("company")
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
