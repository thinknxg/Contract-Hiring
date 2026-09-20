import frappe

def execute(filters=None):
    columns = [{"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Project Site", "width": 140}, {"label": "Site Name", "fieldname": "site_name", "fieldtype": "Data", "options": "", "width": 140}, {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140}, {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140}, {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140}]
    filters = filters or {}
    data = frappe.get_all("Project Site", filters=filters, fields=["name", "site_name", "project", "customer", "warehouse"], order_by="modified desc", limit_page_length=500)
    return columns, data
