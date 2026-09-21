import frappe
from frappe.utils import flt


def delivered_for(so, item_code):
    return flt(frappe.db.sql("""
        select sum(di.qty) from `tabHire Delivery Item` di
        join `tabHire Delivery` d on d.name = di.parent
        where d.sales_order = %s and di.item = %s and d.docstatus = 1
    """, (so, item_code))[0][0])


def returned_for(so, item_code):
    return flt(frappe.db.sql("""
        select sum(ri.qty_to_return) from `tabHire Return Item` ri
        join `tabHire Return` r on r.name = ri.parent
        where r.sales_order = %s and ri.item = %s and r.docstatus = 1
    """, (so, item_code))[0][0])


def returned_breakdown(so, item_code):
    row = frappe.db.sql("""
        select sum(ri.qty_to_return), sum(ri.damage_qty), sum(ri.scrap_qty), sum(ri.lost_qty)
        from `tabHire Return Item` ri
        join `tabHire Return` r on r.name = ri.parent
        where r.sales_order = %s and ri.item = %s and r.docstatus = 1
    """, (so, item_code))[0]
    return [flt(x) for x in row]


def refresh_counters(so):
    for r in frappe.get_all("Sales Order Item", filters={"parent": so}, fields=["name", "item_code"]):
        delivered = delivered_for(so, r.item_code)
        returned, damage, scrap, lost = returned_breakdown(so, r.item_code)
        frappe.db.set_value("Sales Order Item", r.name, {
            "hire_delivered_qty": delivered,
            "hire_returned_qty": returned,
            "hire_damage_qty": damage,
            "hire_scrap_qty": scrap,
            "hire_lost_qty": lost,
            "hire_balance_qty": max(delivered - returned, 0),
        }, update_modified=False)
    update_status(so)


def update_status(so_name):
    docstatus = frappe.db.get_value("Sales Order", so_name, "docstatus")
    if docstatus in (0, 2):
        frappe.db.set_value("Sales Order", so_name, "hire_status", "", update_modified=False)
        return

    ordered = {}
    for r in frappe.get_all("Sales Order Item", filters={"parent": so_name}, fields=["item_code", "qty"]):
        if frappe.db.get_value("Item", r.item_code, "is_stock_item"):
            ordered[r.item_code] = ordered.get(r.item_code, 0) + flt(r.qty)

    if not ordered:
        status = "Confirmed"
    else:
        delivered = {i: delivered_for(so_name, i) for i in ordered}
        returned = {i: returned_for(so_name, i) for i in ordered}
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
    frappe.db.set_value("Sales Order", so_name, "hire_status", status, update_modified=False)


@frappe.whitelist()
def get_deliverable_items(sales_order):
    so = frappe.get_doc("Sales Order", sales_order)
    out = []
    for r in so.items:
        if not frappe.db.get_value("Item", r.item_code, "is_stock_item"):
            continue
        delivered = delivered_for(so.name, r.item_code)
        out.append({
            "item": r.item_code,
            "description": r.description,
            "ordered_qty": flt(r.qty),
            "delivered_qty": delivered,
            "balance_qty": max(flt(r.qty) - delivered, 0),
            "uom": r.uom,
        })
    return out


@frappe.whitelist()
def get_returnable_items(sales_order):
    so = frappe.get_doc("Sales Order", sales_order)
    out = []
    for r in so.items:
        if not frappe.db.get_value("Item", r.item_code, "is_stock_item"):
            continue
        delivered = delivered_for(so.name, r.item_code)
        returned = returned_for(so.name, r.item_code)
        out.append({
            "item": r.item_code,
            "description": r.description,
            "delivered_qty": delivered,
            "returned_qty": returned,
            "balance_qty": max(delivered - returned, 0),
            "uom": r.uom,
        })
    return out
