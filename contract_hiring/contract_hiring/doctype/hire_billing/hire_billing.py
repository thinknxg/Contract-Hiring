import frappe
from frappe.model.document import Document
from frappe.utils import flt

class HireBilling(Document):
    def validate(self):
        if self.hire_order and frappe.db.get_value("Hire Order",self.hire_order,"docstatus")!=1:
            frappe.throw("Hire Order must be submitted before billing.")
        total=0
        for r in self.items:
            r.amount=flt(r.qty)*flt(r.rate)*(flt(r.duration) or 1)
            total+=flt(r.amount)
        self.grand_total=total

    def on_submit(self):
        self.sales_invoice=create_sales_invoice(self)
        self.db_set("sales_invoice",self.sales_invoice)

    def on_cancel(self):
        if self.sales_invoice:
            si=frappe.get_doc("Sales Invoice",self.sales_invoice)
            if si.docstatus==1:
                si.flags.ignore_permissions=True
                si.cancel()

def billing_qty(r):
    if r.rate_type=="M3": return flt(r.calculated_volume)
    if r.rate_type=="SQM": return flt(r.length)*flt(r.breadth)*(flt(r.locations) or 1)
    if r.rate_type=="Lumpsum": return 1
    return flt(r.qty)

@frappe.whitelist()
def make_billing(hire_order):
    ho=frappe.get_doc("Hire Order",hire_order)
    if ho.docstatus!=1: frappe.throw("Submit the Hire Order first.")
    b=frappe.new_doc("Hire Billing")
    b.customer=ho.customer; b.project=ho.project; b.site=ho.site; b.hire_order=ho.name
    b.from_date=ho.billing_start_date or ho.order_date
    b.to_date=ho.billing_end_date or frappe.utils.today()
    for r in ho.items:
        if flt(r.qty):
            b.append("items",{"item":r.item,"description":r.description,"qty":billing_qty(r),"uom":r.uom,
                              "rate_type":r.rate_type,"rate":r.rate,"duration":r.duration or 1,"period":r.period})
    b.insert()
    return b.name

def create_sales_invoice(doc):
    settings=frappe.get_single("Contract Hiring Settings")
    si=frappe.new_doc("Sales Invoice")
    si.customer=doc.customer
    si.posting_date=doc.billing_date
    if doc.billing_date: si.set_posting_time=1
    si.company=frappe.db.get_value("Project",doc.project,"company") or settings.company or frappe.defaults.get_global_default("company")
    si.project=doc.project
    if settings.tax_template:
        from erpnext.controllers.accounts_controller import get_taxes_and_charges
        si.taxes_and_charges=settings.tax_template
        si.extend("taxes",get_taxes_and_charges("Sales Taxes and Charges Template",settings.tax_template))
    for r in doc.items:
        item_code=r.item or settings.default_billing_item
        if not item_code: frappe.throw("Set an Item in every billing row or configure Default Billing Item.")
        si.append("items",{"item_code":item_code,"qty":flt(r.qty)*(flt(r.duration) or 1),
                           "uom":r.uom or frappe.db.get_value("Item",item_code,"stock_uom"),
                           "rate":flt(r.rate),"description":r.description})
    if settings.income_account:
        for row in si.items: row.income_account=settings.income_account
    si.insert(ignore_permissions=True); si.submit()
    return si.name
