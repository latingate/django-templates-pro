# Demo project

```bash
pip install -e ..             # from this folder: installs the package and all its dependencies
python manage.py migrate
python manage.py seed_demo     # constants, blocks, templates, sample records, admin/admin
python manage.py runserver
```

| Page | What it shows |
|---|---|
| `/` | every template rendered for real records in each enabled format |
| `/editors/` | the widget in all presets and skins, plus a custom toolbar, outside the admin |
| `/my-letter/` | a user-facing page where a user writes and renders their own template |
| `/admin/` | templates, blocks (with "used by"), constants, generated documents |

## What's inside

- **Template types** (`demo/doctemplate_types.py`): invoice, customer letter,
  order confirmation and employment certificate. They share a `CUSTOMER` group
  and include per-object locale (`Customer.language`) and currency
  (`Invoice.currency`).
- **Constants** (`samples/manifest.json`): company details and bank details, plus
  computed ones from `demo/constants.py` (`CONSTANTS_PROVIDER`).
- **Blocks** (`samples/blocks/`):
  - `company-letterhead` (logo + constants)
  - `page-footer` (page X of Y; used as the PDF/DOCX page footer)
  - `page-footer-he` (the Hebrew version, for right-to-left templates)
  - `customer-details` (shared by 3 types, with a VAT-ID condition)
  - `bank-details` (nested inside `payment-terms`)
  - `payment-terms` (paid/due conditions)
  - `signature`
- **Templates** (`samples/templates/`):
  - `invoice-standard`: classic theme, repeated table rows, row numbers, discount condition, notes, all 4 formats
  - `invoice-modern`: modern theme with a custom accent, date patterns, currency codes, a timestamp
  - `welcome-letter`: corporate theme, today's date, a list, a condition on open invoices
  - `order-confirmation`: minimal theme, a repeat *section*, text case, HTML + TXT for email
  - `employment-certificate`: a project theme (`northwind`: CSS + Typst style in `settings.py`), current vs. former employee conditions
  - `invoice-hebrew`: **right-to-left** (direction *RTL*, locale `he_IL`), Hebrew labels, a Hebrew footer, ILS currency. Open it for the Hebrew customer (כהן ושות') and for an English one to see per-paragraph direction

The sample HTML is exactly what the editor stores. Read it alongside
`docs/html-contract.md`.

The demo customers use different locales (en_GB, de_DE, fr_FR, he_IL) and
currencies. Open their invoices to see the dates, numbers, currency and
direction change.
