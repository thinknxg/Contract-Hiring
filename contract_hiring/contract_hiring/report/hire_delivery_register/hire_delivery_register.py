import frappe

def execute(filters=None):
    columns = [{"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Hire Delivery", "width": 140}, {"label": "Hire Order", "fieldname": "hire_order", "fieldtype": "Link", "options": "Hire Order", "width": 140}, {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140}, {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Project Site", "width": 140}, {"label": "Delivery Date", "fieldname": "delivery_date", "fieldtype": "Date", "options": "", "width": 140}, {"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140}]
    filters = filters or {}
    data = frappe.get_all("Hire Delivery", filters=filters, fields=["name", "hire_order", "customer", "site", "delivery_date", "stock_entry"], order_by="modified desc", limit_page_length=500)
    return columns, data
