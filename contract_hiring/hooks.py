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

# ---- contract_hiring flow (auto-added) ----
_flow_js = {"Quotation": "public/js/quotation.js", "Sales Order": "public/js/sales_order.js"}
if "doctype_js" not in globals():
    doctype_js = {}
for _dt, _f in _flow_js.items():
    _cur = doctype_js.get(_dt)
    if _cur is None:
        doctype_js[_dt] = _f
    elif isinstance(_cur, str) and _cur != _f:
        doctype_js[_dt] = [_cur, _f]
    elif isinstance(_cur, list) and _f not in _cur:
        _cur.append(_f)

if "doc_events" not in globals():
    doc_events = {}
for _dt in ("Quotation", "Sales Order"):
    _ev = doc_events.setdefault(_dt, {})
    _h = "contract_hiring.flow_rules.apply_rules"
    _cur = _ev.get("before_validate")
    if _cur is None:
        _ev["before_validate"] = _h
    elif isinstance(_cur, str) and _cur != _h:
        _ev["before_validate"] = [_cur, _h]
    elif isinstance(_cur, list) and _h not in _cur:
        _cur.append(_h)

_am = globals().get("after_migrate")
_fh = "contract_hiring.flow_fields.ensure_flow_fields"
if _am is None:
    after_migrate = [_fh]
elif isinstance(_am, str):
    after_migrate = [_am] if _am == _fh else [_am, _fh]
elif _fh not in _am:
    after_migrate = list(_am) + [_fh]

# ---- contract_hiring: hire_status lifecycle on Sales Order ----
doc_events.setdefault("Sales Order", {})
doc_events["Sales Order"]["on_submit"] = "contract_hiring.hiring.on_sales_order_submit"
doc_events["Sales Order"]["on_cancel"] = "contract_hiring.hiring.on_sales_order_cancel"
