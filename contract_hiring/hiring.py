import frappe


def on_sales_order_submit(doc, method=None):
    if getattr(doc, "hiring_type", None):
        doc.db_set("hire_status", "Confirmed", update_modified=False)


def on_sales_order_cancel(doc, method=None):
    if getattr(doc, "hiring_type", None):
        doc.db_set("hire_status", "", update_modified=False)
