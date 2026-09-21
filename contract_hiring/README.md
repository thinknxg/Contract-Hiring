# Contract Hiring / Scaffolding Rental — ERPNext v16

Hiring workflow built on native ERPNext Quotation and Sales Order. Hire-specific documents handle delivery, return, service and billing.

## Complete connected flow

Customer
→ Project
→ Project Site (auto-creates the site Warehouse)
→ Quotation (hiring_type set)
→ Sales Order
→ Fulfillment:
   - Stock lines: Hire Delivery → Stock Entry (Main Stock → Site Warehouse)
   - Service lines (M3 / SQM / Lumpsum): Service Delivery
→ Hire Return → Stock Entry (Site Warehouse → Main / Damage / Scrap / Lost Warehouse)
→ Direct Invoice (Sales Invoice for damage / scrap / lost, left as Draft for review)
→ Hire Billing → Sales Invoice (Contract Invoice, submitted automatically)

## Hiring types (Quotation / Sales Order field `hiring_type`)

- Material Sale → invoice type Sale Invoice (no returns)
- Material Hire → invoice type Hire Invoice
- Contract Hire → invoice type Contract Invoice

The Sales Order's `hiring_type` decides the invoice type on Hire Billing.

## Sales Order status (`hire_status`)

Confirmed → Partially Delivered → Delivered → Partially Returned → Closed

Only stock items count towards delivery and return status. A pure-service order stays at Confirmed.

## Calculation design

Length, Breadth and Height are calculation fields. They do NOT replace Qty, UOM, Rate Type, Rate, Duration or Period. On Quotation and Sales Order the dimension quantity is written into the line Qty before validation (flow_rules.apply_rules).

- M3 = Length × Breadth × Height × Locations. Billed per Period (Day / Month / Year) from the Service Delivery date.
- SQM = Length × Breadth × Locations. One-time charge.
- Lumpsum = one-time charge.
- Nos = delivered Qty × Rate, billed by quantity.
- Day / Month = quantity on hire each day × Rate, prorated over the billing period.

## Hire Return classification

Each returned quantity is split into Normal, Damage, Scrap, Lost and Excess. Normal goes back to the Main Stock Warehouse. Damage, Scrap and Lost go to their own warehouses from Contract Hiring Settings. Damage, Scrap and Lost quantities are invoiced through Direct Invoice at the item's standard rate (valuation rate if none).

## Billing rules

- Hire Billing is periodic. A period already billed cannot be billed again.
- One-time lines are billed once.
- Contract Hire service lines are skipped until a Service Delivery exists.
- Billing start and end dates on the Sales Order act as a floor and a cap.

## Do not use native stock documents for hire items

Create deliveries and returns only through Hire Delivery / Hire Return. A native Delivery Note bypasses hire tracking and falls back to the Item Default warehouse, which usually holds no stock.

## Install

```bash
cd ~/frappe-bench-v16
bench get-app /path/to/contract_hiring_v16_complete.zip
bench --site your-site install-app contract_hiring
bench --site your-site migrate
bench clear-cache
bench restart
```

## First-time setup

ERPNext still requires the organization's own Company, Customer, Project, Item and accounting masters. In Contract Hiring Settings configure:
- Main Stock Warehouse
- Damage Warehouse
- Scrap Warehouse
- Lost Warehouse
- Default Billing Item (optional)
- Income Account (optional)
- Tax Template (optional)
- Company

Create a Project Site for each hiring site. The app creates a dedicated Warehouse for the site.
