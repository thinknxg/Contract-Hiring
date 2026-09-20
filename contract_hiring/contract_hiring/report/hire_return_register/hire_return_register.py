import frappe

def execute(filters=None):
    columns = [{"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Hire Return", "width": 140}, {"label": "Hire Order", "fieldname": "hire_order", "fieldtype": "Link", "options": "Hire Order", "width": 140}, {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140}, {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Project Site", "width": 140}, {"label": "Return Date", "fieldname": "return_date", "fieldtype": "Date", "options": "", "width": 140}, {"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140}]
    filters = filters or {}
    data = frappe.get_all("Hire Return", filters=filters, fields=["name", "hire_order", "customer", "site", "return_date", "stock_entry"], order_by="modified desc", limit_page_length=500)
    return columns, data
