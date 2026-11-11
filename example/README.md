# Demo project

```bash
python run_demo.py             # does everything below, then starts the server
```

Or step by step, in an active virtual environment:

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
| `/docs/` | the documentation: every Markdown file of the repository, rendered and in reading order |
| `/admin/` | templates, blocks (with "used by"), constants, generated documents |

What to open and what to look for in each template is in
[docs/samples.md](../docs/samples.md#demo-project).

## How the demo pages get their data

`/editors/` and the editor's **Preview** never touch real records. The chips
show field labels, and the preview is filled with the `sample=` values from
the schemas in `demo/doctemplate_types.py` (for example the `CUSTOMER`
group's "Jane Roe").

Real records are used by the links on `/`, which point at
`/doc/<slug>/<pk>.<fmt>`, e.g. `/doc/invoice-hebrew/1.html`. The view is
`demo.views.document`:

1. It loads the `DocumentTemplate` with that slug.
2. `SOURCES` in `demo/views.py` maps the template's type to a model
   (`"invoice"` → `Invoice`), and the view loads that model's row with the
   given `pk`.
3. It calls `render_to_response(tpl, obj, fmt=fmt, request=request)`.
4. `InvoiceTemplate.build_context()` turns the invoice, its lines and its
   customer into the plain dict the template reads.

`SOURCES` is demo code, not part of the package: in your project the view
decides which object to pass to `render()`.

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

## The documentation page

`/docs/` lists every `.md` file found in the repository root, `docs/`,
`example/` and `frontend/`, and `/docs/<name>/` shows one of them. The order
is set by `SECTIONS` in `demo/docs.py`; a file that is not listed there still
appears, under *More*. Links between the files work inside the viewer. The
pages are converted by `demo/markdown.py`, a small converter written for
these files, so the demo needs no extra package.

The demo customers use different locales (en_GB, de_DE, fr_FR, he_IL) and
currencies. Open their invoices to see the dates, numbers, currency and
direction change.
