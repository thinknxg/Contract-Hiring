import frappe

def execute(filters=None):
    columns = [{"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Hire Order", "width": 140}, {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140}, {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140}, {"label": "Site", "fieldname": "site", "fieldtype": "Link", "options": "Project Site", "width": 140}, {"label": "Billing Start Date", "fieldname": "billing_start_date", "fieldtype": "Date", "options": "", "width": 140}, {"label": "Billing End Date", "fieldname": "billing_end_date", "fieldtype": "Date", "options": "", "width": 140}, {"label": "Status", "fieldname": "status", "fieldtype": "Data", "options": "", "width": 140}]
    filters = filters or {}
    data = frappe.get_all("Hire Order", filters=filters, fields=["name", "customer", "project", "site", "billing_start_date", "billing_end_date", "status"], order_by="modified desc", limit_page_length=500)
    return columns, data
