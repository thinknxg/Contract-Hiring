import calendar
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from contract_hiring.hiring_flow import delivered_for

INVOICE_TYPES = {"Material Sale": "Sale Invoice", "Material Hire": "Hire Invoice", "Contract Hire": "Contract Invoice"}


def billing_qty(r):
    return flt(r.qty)


def is_service_row(r):
    return r.rate_type in ("M3", "SQM", "Lumpsum") or not frappe.db.get_value("Item", r.item_code, "is_stock_item")


def unit_fraction(d, unit):
    if unit == "Month":
        return 1.0 / calendar.monthrange(d.year, d.month)[1]
    if unit == "Year":
        return 1.0 / (366 if calendar.isleap(d.year) else 365)
    return 1.0


def billed_rows(so_name, exclude=None):
    out = {}
    rows = frappe.db.sql("""
        select bi.order_row, bi.billing_mode, bi.billed_to, bi.qty
        from `tabHire Billing Item` bi join `tabHire Billing` b on b.name = bi.parent
        where b.sales_order = %(so)s and b.docstatus = 1 and b.name != %(ex)s and ifnull(bi.order_row, '') != ''
    """, {"so": so_name, "ex": exclude or ""}, as_dict=True)
    for x in rows:
        o = out.setdefault(x.order_row, {"through": None, "qty": 0.0})
        if x.billing_mode == "Periodic":
            if x.billed_to and (o["through"] is None or getdate(x.billed_to) > o["through"]):
                o["through"] = getdate(x.billed_to)
        else:
            o["qty"] += flt(x.qty)
    return out


def stock_timeline(so_name, item_code):
    deliveries = [(getdate(x.delivery_date or nowdate()), flt(x.qty)) for x in frappe.db.sql("""
        select d.delivery_date, di.qty from `tabHire Delivery Item` di
        join `tabHire Delivery` d on d.name = di.parent
        where d.sales_order = %s and di.item = %s and d.docstatus = 1""", (so_name, item_code), as_dict=True)]
    returns = [(getdate(x.rent_end or nowdate()), flt(x.qty)) for x in frappe.db.sql("""
        select coalesce(r.rent_up_to, r.return_date) as rent_end, ri.qty_to_return as qty
        from `tabHire Return Item` ri join `tabHire Return` r on r.name = ri.parent
        where r.sales_order = %s and ri.item = %s and r.docstatus = 1""", (so_name, item_code), as_dict=True)]
    return deliveries, returns


def default_from_date(so):
    dates = []
    if so.get("hire_billing_start"):
        dates.append(getdate(so.hire_billing_start))
    first = frappe.db.sql("select min(delivery_date) from `tabHire Delivery` where sales_order = %s and docstatus = 1", so.name)[0][0]
    if first:
        dates.append(getdate(first))
    for r in so.items:
        if r.get("serviced_on"):
            dates.append(getdate(r.serviced_on))
    return min(dates) if dates else getdate(so.get("transaction_date") or nowdate())


def compute_items(so, from_date, to_date):
    from_date, to_date = getdate(from_date), getdate(to_date)
    billed = billed_rows(so.name)
    floor = getdate(so.hire_billing_start) if so.get("hire_billing_start") else None
    cap = getdate(so.hire_billing_end) if so.get("hire_billing_end") else None
    last_return_end = None
    if so.get("hire_status") == "Closed":
        v = frappe.db.sql("select max(coalesce(rent_up_to, return_date)) from `tabHire Return` where sales_order = %s and docstatus = 1", so.name)[0][0]
        last_return_end = getdate(v) if v else None
    items, notes = [], []
    for r in so.items:
        done = billed.get(r.name, {"through": None, "qty": 0.0})
        serviced_on = getdate(r.serviced_on) if r.get("serviced_on") else None
        if so.hiring_type == "Contract Hire" and is_service_row(r) and not serviced_on:
            notes.append(f"Line {r.idx} ({r.item_code}) skipped: no Service Delivery yet.")
            continue
        base = {"order_row": r.name, "item": r.item_code, "uom": r.uom, "rate_type": r.rate_type, "duration": 1}
        if r.rate_type in ("SQM", "Lumpsum"):
            if flt(done["qty"]) > 0 or not flt(r.amount):
                continue
            items.append(dict(base, description=f"{r.description or r.item_code}: one-time charge", qty=1,
                              rate=flt(r.amount), billing_mode="One-time"))
        elif r.rate_type == "Nos":
            qty = delivered_for(so.name, r.item_code) - flt(done["qty"])
            if qty > 0:
                items.append(dict(base, description=r.description or r.item_code, qty=qty, rate=flt(r.rate), billing_mode="Quantity"))
        else:
            unit = r.rate_type if r.rate_type in ("Day", "Month") else (r.period or "")
            if unit not in ("Day", "Month", "Year"):
                frappe.throw(f"Order line {r.idx} ({r.item_code}): choose a Period (Day, Month or Year) for this {r.rate_type} line.")
            start, end = from_date, to_date
            if floor: start = max(start, floor)
            if cap: end = min(end, cap)
            if done["through"]: start = max(start, done["through"] + timedelta(days=1))
            if r.rate_type == "M3":
                if serviced_on: start = max(start, serviced_on)
                if last_return_end: end = min(end, last_return_end)
                volume = billing_qty(r)
                on_hire = lambda d, v=volume: v
            else:
                deliveries, returns = stock_timeline(so.name, r.item_code)
                on_hire = lambda d, dl=deliveries, rt=returns: sum(q for dt, q in dl if dt <= d) - sum(q for dt, q in rt if dt < d)
            if start > end:
                continue
            units, d = 0.0, start
            while d <= end:
                q = on_hire(d)
                if q > 0:
                    units += q * unit_fraction(d, unit)
                d += timedelta(days=1)
            if units <= 0:
                continue
            items.append(dict(base, description=f"{r.description or r.item_code}: {start} to {end} ({unit} rate)",
                              qty=flt(units, 3), rate=flt(r.rate), period=unit, billing_mode="Periodic",
                              billed_from=start, billed_to=end))
    return items, notes


class HireBilling(Document):
    def validate(self):
        if self.sales_order and frappe.db.get_value("Sales Order", self.sales_order, "docstatus") != 1:
            frappe.throw("Sales Order must be submitted before billing.")
        if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date.")
        htype = frappe.db.get_value("Sales Order", self.sales_order, "hiring_type") or self.hiring_type
        self.invoice_type = INVOICE_TYPES.get(htype, "")
        billed = billed_rows(self.sales_order, exclude=self.name)
        total = 0
        for r in self.items:
            r.amount = flt(r.qty) * flt(r.rate) * (flt(r.duration) or 1)
            total += flt(r.amount)
            if not r.order_row:
                continue
            prior = billed.get(r.order_row, {})
            if r.billing_mode == "Periodic" and prior.get("through") and r.billed_from and getdate(r.billed_from) <= prior["through"]:
                frappe.throw(f"Row {r.idx}: this line is already billed up to {prior['through']}.")
            if r.billing_mode == "One-time" and flt(prior.get("qty")):
                frappe.throw(f"Row {r.idx}: this one-time line has already been billed.")
        self.grand_total = total

    def on_submit(self):
        self.sales_invoice = create_sales_invoice(self)
        self.db_set("sales_invoice", self.sales_invoice)

    def on_cancel(self):
        if self.sales_invoice:
            si = frappe.get_doc("Sales Invoice", self.sales_invoice)
            if si.docstatus == 1:
                si.flags.ignore_permissions = True
                si.cancel()


@frappe.whitelist()
def get_billing_items(sales_order, from_date=None, to_date=None):
    so = frappe.get_doc("Sales Order", sales_order)
    if so.docstatus != 1:
        frappe.throw("Submit the Sales Order first.")
    from_date = from_date or default_from_date(so)
    to_date = to_date or nowdate()
    items, notes = compute_items(so, from_date, to_date)
    return {"items": items, "notes": notes, "from_date": str(getdate(from_date)), "to_date": str(getdate(to_date))}


@frappe.whitelist()
def make_billing(sales_order, from_date=None, to_date=None):
    so = frappe.get_doc("Sales Order", sales_order)
    res = get_billing_items(sales_order, from_date, to_date)
    if not res["items"]:
        frappe.throw("Nothing to bill for this period. " + " ".join(res["notes"]))
    b = frappe.new_doc("Hire Billing")
    b.customer, b.project, b.site, b.sales_order = so.customer, so.project, so.hiring_site, so.name
    b.billing_date = nowdate()
    b.from_date, b.to_date = res["from_date"], res["to_date"]
    for it in res["items"]:
        b.append("items", it)
    b.insert()
    if res["notes"]:
        frappe.msgprint("<br>".join(res["notes"]))
    return b.name


def create_sales_invoice(doc):
    settings = frappe.get_single("Contract Hiring Settings")
    si = frappe.new_doc("Sales Invoice")
    si.customer = doc.customer
    si.posting_date = doc.billing_date
    if doc.billing_date: si.set_posting_time = 1
    si.company = frappe.db.get_value("Sales Order", doc.sales_order, "company") or settings.company or frappe.defaults.get_global_default("company")
    si.project = doc.project
    si.remarks = f"{doc.invoice_type or 'Invoice'} {doc.name}: {doc.from_date} to {doc.to_date}"
    si.hiring_invoice_type = doc.invoice_type
    si.hiring_sales_order = doc.sales_order
    si.hire_billing = doc.name
    si.hire_period_from = doc.from_date
    si.hire_period_to = doc.to_date
    if settings.tax_template:
        from erpnext.controllers.accounts_controller import get_taxes_and_charges
        si.taxes_and_charges = settings.tax_template
        si.extend("taxes", get_taxes_and_charges("Sales Taxes and Charges Template", settings.tax_template))
    for r in doc.items:
        item_code = r.item or settings.default_billing_item
        if not item_code: frappe.throw("Set an Item in every billing row or configure Default Billing Item.")
        si.append("items", {"item_code": item_code, "qty": flt(r.qty) * (flt(r.duration) or 1),
                            "uom": r.uom or frappe.db.get_value("Item", item_code, "stock_uom"),
                            "rate": flt(r.rate), "description": r.description})
    if settings.income_account:
        for row in si.items: row.income_account = settings.income_account
    si.insert(ignore_permissions=True); si.submit()
    return si.name
