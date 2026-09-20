app_name = "contract_hiring"
app_title = "Contract Hiring"
app_publisher = "Contract Hiring"
app_description = "Integrated contract hiring, scaffolding rental, site stock and billing workflow for ERPNext"
app_email = "support@example.com"
app_license = "MIT"

after_install = "contract_hiring.install.after_install"

doctype_js = {
    "Project": "public/js/project.js",
    "Customer": "public/js/customer.js",
}

scheduler_events = {
    "daily": [
        "contract_hiring.utils.update_hire_balances"
    ]
}
