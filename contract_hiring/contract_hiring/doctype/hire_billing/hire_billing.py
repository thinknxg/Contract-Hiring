import calendar
from datetime import timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from contract_hiring.contract_hiring.doctype.hire_order.hire_order import delivered_for

INVOICE_TYPES = {"Material Sale": "Sale Invoice", "Material Hire": "Hire Invoice", "Contract Hire": "Contract Invoice"}


def billing_qty(r):
    if r.rate_type == "M3": return flt(r.calculated_volume)
    if r.rate_type == "SQM": return flt(r.length) * flt(r.breadth) * (flt(r.locations) or 1)
    if r.rate_type == "Lumpsum": return 1
    return flt(r.qty)


def is_service_row(r):
    return r.rate_type in ("M3", "SQM", "Lumpsum") or not frappe.db.get_value("Item", r.item, "is_stock_item")


def unit_fraction(d, unit):
    if unit == "Month":
        return 1.0 / calendar.monthrange(d.year, d.month)[1]
    if unit == "Year":
        return 1.0 / (366 if calendar.isleap(d.year) else 365)
    return 1.0


def billed_rows(ho_name, exclude=None):
    """order_row -> {"through": last billed date of periodic bills, "qty": quantity billed once or by quantity}"""
    out = {}
    rows = frappe.db.sql("""
        select bi.order_row, bi.billing_mode, bi.billed_to, bi.qty
        from `tabHire Billing Item` bi join `tabHire Billing` b on b.name = bi.parent
        where b.hire_order = %(ho)s and b.docstatus = 1 and b.name != %(ex)s and ifnull(bi.order_row, '') != ''
    """, {"ho": ho_name, "ex": exclude or ""}, as_dict=True)
    for x in rows:
        o = out.setdefault(x.order_row, {"through": None, "qty": 0.0})
        if x.billing_mode == "Periodic":
            if x.billed_to and (o["through"] is None or getdate(x.billed_to) > o["through"]):
                o["through"] = getdate(x.billed_to)
        else:
            o["qty"] += flt(x.qty)
    return out


def stock_timeline(ho_name, item):
    deliveries = [(getdate(x.delivery_date or nowdate()), flt(x.qty)) for x in frappe.db.sql("""
        select d.delivery_date, di.qty from `tabHire Delivery Item` di
        join `tabHire Delivery` d on d.name = di.parent
        where d.hire_order = %s and di.item = %s and d.docstatus = 1""", (ho_name, item), as_dict=True)]
    returns = [(getdate(x.rent_end or nowdate()), flt(x.qty)) for x in frappe.db.sql("""
        select coalesce(r.rent_up_to, r.return_date) as rent_end, ri.qty_to_return as qty
        from `tabHire Return Item` ri join `tabHire Return` r on r.name = ri.parent
        where r.hire_order = %s and ri.item = %s and r.docstatus = 1""", (ho_name, item), as_dict=True)]
    return deliveries, returns


def default_from_date(ho):
    dates = []
    if ho.get("billing_start_date"):
        dates.append(getdate(ho.billing_start_date))
    first = frappe.db.sql("select min(delivery_date) from `tabHire Delivery` where hire_order = %s and docstatus = 1", ho.name)[0][0]
    if first:
        dates.append(getdate(first))
    for r in ho.items:
        if r.get("serviced_on"):
            dates.append(getdate(r.serviced_on))
    return min(dates) if dates else getdate(ho.get("order_date") or nowdate())


def compute_items(ho, from_date, to_date):
    from_date, to_date = getdate(from_date), getdate(to_date)
    billed = billed_rows(ho.name)
    floor = getdate(ho.billing_start_date) if ho.get("billing_start_date") else None
    cap = getdate(ho.billing_end_date) if ho.get("billing_end_date") else None
    last_return_end = None
    if ho.status == "Closed":
        v = frappe.db.sql("select max(coalesce(rent_up_to, return_date)) from `tabHire Return` where hire_order = %s and docstatus = 1", ho.name)[0][0]
        last_return_end = getdate(v) if v else None
    items, notes = [], []
    for r in ho.items:
        done = billed.get(r.name, {"through": None, "qty": 0.0})
        serviced_on = getdate(r.serviced_on) if r.get("serviced_on") else None
        if ho.hiring_type == "Contract Hire" and is_service_row(r) and not serviced_on:
            notes.append(f"Line {r.idx} ({r.item}) skipped: no Service Delivery yet.")
            continue
        base = {"order_row": r.name, "item": r.item, "uom": r.uom, "rate_type": r.rate_type, "duration": 1}
        if r.rate_type in ("SQM", "Lumpsum"):
            if flt(done["qty"]) > 0 or not flt(r.amount):
                continue
            items.append(dict(base, description=f"{r.description or r.item}: one-time charge", qty=1,
                              rate=flt(r.amount), billing_mode="One-time"))
        elif r.rate_type == "Nos":
            qty = delivered_for(ho.name, r.item) - flt(done["qty"])
            if qty > 0:
                items.append(dict(base, description=r.description or r.item, qty=qty, rate=flt(r.rate), billing_mode="Quantity"))
        else:
            unit = r.rate_type if r.rate_type in ("Day", "Month") else (r.period or "")
            if unit not in ("Day", "Month", "Year"):
                frappe.throw(f"Order line {r.idx} ({r.item}): choose a Period (Day, Month or Year) for this {r.rate_type} line.")
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
                deliveries, returns = stock_timeline(ho.name, r.item)
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
            items.append(dict(base, description=f"{r.description or r.item}: {start} to {end} ({unit} rate)",
                              qty=flt(units, 3), rate=flt(r.rate), period=unit, billing_mode="Periodic",
                              billed_from=start, billed_to=end))
    return items, notes


class HireBilling(Document):
    def validate(self):
        if self.hire_order and frappe.db.get_value("Hire Order", self.hire_order, "docstatus") != 1:
            frappe.throw("Hire Order must be submitted before billing.")
        if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date.")
        htype = self.hiring_type or frappe.db.get_value("Hire Order", self.hire_order, "hiring_type")
        self.invoice_type = INVOICE_TYPES.get(htype, "")
        billed = billed_rows(self.hire_order, exclude=self.name)
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
def get_billing_items(hire_order, from_date=None, to_date=None):
    ho = frappe.get_doc("Hire Order", hire_order)
    if ho.docstatus != 1:
        frappe.throw("Submit the Hire Order first.")
    from_date = from_date or default_from_date(ho)
    to_date = to_date or nowdate()
    items, notes = compute_items(ho, from_date, to_date)
    return {"items": items, "notes": notes, "from_date": str(getdate(from_date)), "to_date": str(getdate(to_date))}


@frappe.whitelist()
def make_billing(hire_order, from_date=None, to_date=None):
    ho = frappe.get_doc("Hire Order", hire_order)
    res = get_billing_items(hire_order, from_date, to_date)
    if not res["items"]:
        frappe.throw("Nothing to bill for this period. " + " ".join(res["notes"]))
    b = frappe.new_doc("Hire Billing")
    b.customer, b.project, b.site, b.hire_order = ho.customer, ho.project, ho.site, ho.name
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
    si.company = frappe.db.get_value("Project", doc.project, "company") or settings.company or frappe.defaults.get_global_default("company")
    si.project = doc.project
    si.remarks = f"{doc.invoice_type or 'Invoice'} {doc.name}: {doc.from_date} to {doc.to_date}"
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
