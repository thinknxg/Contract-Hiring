import frappe
from frappe.model.document import Document

class ProjectSite(Document):
    def validate(self):
        if self.project:
            self.customer = frappe.db.get_value("Project", self.project, "customer")

    def on_update(self):
        if not self.auto_create_warehouse or self.warehouse or not self.project:
            return
        company = frappe.db.get_value("Project", self.project, "company") or frappe.defaults.get_global_default("company")
        if not company:
            return
        wh = frappe.db.get_value("Warehouse", {"warehouse_name": self.site_name, "company": company})
        if not wh:
            try:
                wh_doc = frappe.get_doc({
                    "doctype":"Warehouse",
                    "warehouse_name":self.site_name,
                    "company":company,
                    "is_group":0
                }).insert(ignore_permissions=True)
                wh = wh_doc.name
            except Exception:
                wh = None
        if wh:
            frappe.db.set_value(self.doctype, self.name, "warehouse", wh, update_modified=False)
