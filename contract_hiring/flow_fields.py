import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

TYPES = "\nMaterial Sale\nMaterial Hire\nContract Hire"
RATE_TYPES = "\nNos\nDay\nMonth\nM3\nSQM\nLumpsum"


def _line_fields():
    return [
        dict(fieldname="rate_type", label="Rate Type", fieldtype="Select", options=RATE_TYPES, insert_after="uom", in_list_view=1),
        dict(fieldname="length", label="Length", fieldtype="Float", insert_after="rate_type", in_list_view=1),
        dict(fieldname="breadth", label="Breadth", fieldtype="Float", insert_after="length", in_list_view=1),
        dict(fieldname="height", label="Height", fieldtype="Float", insert_after="breadth", in_list_view=1),
        dict(fieldname="locations", label="No. of Locations", fieldtype="Float", default="1", insert_after="height"),
        dict(fieldname="period", label="Period", fieldtype="Select", options="\nDay\nMonth\nYear", insert_after="locations"),
        dict(fieldname="duration", label="Duration", fieldtype="Int", insert_after="period"),
    ]


def _tracking_fields():
    out, prev = [], "duration"
    for fieldname, label in [("hire_delivered_qty", "Delivered (Hire)"), ("hire_returned_qty", "Returned (Hire)"),
                             ("hire_damage_qty", "Damage"), ("hire_scrap_qty", "Scrap"), ("hire_lost_qty", "Lost"),
                             ("hire_balance_qty", "On Hire Balance")]:
        out.append(dict(fieldname=fieldname, label=label, fieldtype="Float", read_only=1, no_copy=1, insert_after=prev))
        prev = fieldname
    out.append(dict(fieldname="serviced_on", label="Serviced On", fieldtype="Date", read_only=1, no_copy=1, insert_after=prev))
    out.append(dict(fieldname="service_delivery", label="Service Delivery", fieldtype="Link", options="Service Delivery",
                    read_only=1, no_copy=1, insert_after="serviced_on"))
    return out


def ensure_flow_fields():
    create_custom_fields(
        {
            "Lead": [dict(fieldname="hiring_type", label="Type of Lead", fieldtype="Select", options=TYPES,
                          insert_after="status", in_standard_filter=1)],
            "Quotation": [dict(fieldname="hiring_type", label="Type of Quotation", fieldtype="Select", options=TYPES,
                               insert_after="order_type", in_standard_filter=1)],
            "Quotation Item": _line_fields(),
            "Sales Order": [
                dict(fieldname="hiring_type", label="Type of Order", fieldtype="Select", options=TYPES,
                     insert_after="order_type", in_standard_filter=1),
                dict(fieldname="hire_status", label="Hire Status", fieldtype="Select", read_only=1, no_copy=1,
                     options="\nConfirmed\nPartially Delivered\nDelivered\nPartially Returned\nClosed",
                     insert_after="hiring_type", in_standard_filter=1),
                dict(fieldname="hiring_site", label="Site", fieldtype="Link", options="Project Site", insert_after="hire_status"),
                dict(fieldname="hire_billing_start", label="Billing Start Date", fieldtype="Date", insert_after="hiring_site"),
                dict(fieldname="hire_billing_end", label="Billing End Date", fieldtype="Date", insert_after="hire_billing_start"),
            ],
            "Sales Order Item": _line_fields() + _tracking_fields(),
            "Sales Invoice": [
                dict(fieldname="hiring_section", label="Hiring", fieldtype="Section Break", insert_after="remarks", collapsible=1),
                dict(fieldname="hiring_invoice_type", label="Hiring Invoice Type", fieldtype="Select", read_only=1,
                     options="\nSale Invoice\nHire Invoice\nContract Invoice\nDirect Invoice",
                     insert_after="hiring_section", in_standard_filter=1),
                dict(fieldname="hiring_sales_order", label="Sales Order (Hiring)", fieldtype="Link", options="Sales Order",
                     read_only=1, insert_after="hiring_invoice_type"),
                dict(fieldname="hire_billing", label="Hire Billing", fieldtype="Link", options="Hire Billing", read_only=1, insert_after="hiring_sales_order"),
                dict(fieldname="hire_return", label="Hire Return", fieldtype="Link", options="Hire Return", read_only=1, insert_after="hire_billing"),
                dict(fieldname="hiring_column", fieldtype="Column Break", insert_after="hire_return"),
                dict(fieldname="hire_period_from", label="Hire Period From", fieldtype="Date", read_only=1, insert_after="hiring_column"),
                dict(fieldname="hire_period_to", label="Hire Period To", fieldtype="Date", read_only=1, insert_after="hire_period_from"),
            ],
        },
        update=True,
    )
