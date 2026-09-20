# Contract Hiring / Scaffolding Rental — ERPNext v16

## Complete connected flow

Customer
→ Project
→ Project Site
→ Contract Hiring Quotation
→ Hire Order
→ Hire Delivery
→ ERPNext Stock Entry
→ Site Warehouse
→ Hire Return
→ ERPNext Stock Entry
→ Periodic Hire Billing
→ ERPNext Sales Invoice

## Important calculation design

Length, Breadth and Height are additional calculation fields. They do NOT replace Qty, UOM, Rate Type, Rate, Duration or Period.

Supported calculation types:
- M3 = Length × Breadth × Height × Locations × Rate
- SQM = Length × Breadth × Locations × Rate
- Nos = Qty × Rate
- Day = Qty × Rate × Duration
- Month = Qty × Rate × Duration
- Lumpsum = Rate

## User navigation

Buttons are provided on submitted documents:
- Quotation → Create Hire Order / Create Revision
- Hire Order → Create Hire Delivery / Create Hire Return / Create Hire Billing
- Delivery → Open Stock Entry
- Return → Open Stock Entry
- Billing → Open Sales Invoice
- Project → Create Project Site
- Customer → Contract Hiring Quotations

The target documents keep the source links so users can move backward and forward through the transaction chain.

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

Create a Project Site for each hiring site. The app can create a dedicated Warehouse for the site.

After that the operational users can follow the connected buttons instead of manually copying information.
