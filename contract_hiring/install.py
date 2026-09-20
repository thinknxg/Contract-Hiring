import frappe

def after_install():
    frappe.db.commit()
    frappe.msgprint("Contract Hiring installed. Open Contract Hiring Settings to configure your defaults.")
