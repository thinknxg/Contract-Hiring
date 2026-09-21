import frappe
from frappe.model.document import Document

from contract_hiring.contract_hiring.doctype.hire_billing.hire_billing import billing_qty


def is_service_row(r):
    return r.rate_type in ("M3", "SQM", "Lumpsum") or not frappe.db.get_value("Item", r.item_code, "is_stock_item")


class ServiceDelivery(Document):
    def validate(self):
        so = frappe.get_doc("Sales Order", self.sales_order)
        if so.docstatus != 1:
            frappe.throw(f"Sales Order {so.name} must be submitted first.")
        if so.hiring_type != "Contract Hire":
            frappe.throw("Service Delivery applies to Contract Hire orders only.")
        self.customer, self.project, self.site = so.customer, so.project, so.hiring_site
        rows = {r.name: r for r in so.items}
        seen = set()
        for r in self.items:
            if r.order_row not in rows:
                frappe.throw(f"Row {r.idx}: this is not a line of Sales Order {so.name}.")
            if r.order_row in seen:
                frappe.throw(f"Row {r.idx}: this order line is listed twice.")
            seen.add(r.order_row)
            done = rows[r.order_row].get("service_delivery")
            if done and done != self.name and frappe.db.get_value("Service Delivery", done, "docstatus") == 1:
                frappe.throw(f"Row {r.idx}: this order line was already delivered in {done}.")

    def on_submit(self):
        for r in self.items:
            frappe.db.set_value("Sales Order Item", r.order_row,
                                {"serviced_on": self.service_date, "service_delivery": self.name}, update_modified=False)

    def on_cancel(self):
        for r in self.items:
            frappe.db.set_value("Sales Order Item", r.order_row,
                                {"serviced_on": None, "service_delivery": None}, update_modified=False)


@frappe.whitelist()
def make_service_delivery(sales_order):
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus != 1:
        frappe.throw("Submit the Sales Order first.")
    if so.hiring_type != "Contract Hire":
        frappe.throw("Service Delivery applies to Contract Hire orders only.")
    sd = frappe.new_doc("Service Delivery")
    sd.sales_order = so.name
    sd.customer, sd.project, sd.site = so.customer, so.project, so.hiring_site
    for r in so.items:
        done = r.get("service_delivery")
        if done and frappe.db.get_value("Service Delivery", done, "docstatus") == 1:
            continue
        if is_service_row(r):
            sd.append("items", {"order_row": r.name, "item": r.item_code, "description": r.description,
                                "rate_type": r.rate_type, "billing_qty": billing_qty(r), "uom": r.uom})
    if not sd.items:
        frappe.throw("Nothing left to deliver as a service on this order.")
    sd.insert()
    return sd.name
