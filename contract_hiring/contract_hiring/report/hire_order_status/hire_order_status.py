import frappe

def execute(filters=None):
    columns = [{"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Hire Order", "width": 140}, {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140}, {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140}, {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Project Site", "width": 140}, {"label": "Status", "fieldname": "status", "fieldtype": "Data", "options": "", "width": 140}, {"label": "Order Date", "fieldname": "order_date", "fieldtype": "Date", "options": "", "width": 140}, {"label": "Total Ordered Amount", "fieldname": "total_ordered_amount", "fieldtype": "Currency", "options": "", "width": 140}]
    filters = filters or {}
    data = frappe.get_all("Hire Order", filters=filters, fields=["name", "customer", "project", "site", "status", "order_date", "total_ordered_amount"], order_by="modified desc", limit_page_length=500)
    return columns, data
