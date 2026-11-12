# Samples, demo and examples

The repository has three sets of ready-made content. This page says what each
one is for and how to use it.

| Set | Where | Use it to |
|---|---|---|
| [Packaged samples](#packaged-samples) | `templates_pro.samples` (installed with pip) | get working templates into **your own project** in two commands |
| [Demo project](#demo-project) | `example/` (repository), `python -m templates_pro.demo` (pip) | see every feature running, with real records, before integrating |
| [Stored-HTML files](#the-sample-html-files) | `example/demo/samples/`, `src/templates_pro/samples/content/` | read or copy the markup the editor produces |

There are also [code examples](#code-examples) to copy from.

## Packaged samples

Starter content that ships inside the pip package. It needs no models: the
sample types take plain dicts.

### Load them

```python
INSTALLED_APPS = [
    # ...
    "templates_pro",
    "templates_pro.samples",     # registers the sample template types
]
```

```bash
python manage.py templates_pro_samples
```

The command reports what it created. Running it again changes nothing.

### What you get

**Four template types** (keys start with `sample_`):

| Key | Fields | Lists |
|---|---|---|
| `sample_invoice` | `invoice.*` (number, dates, totals, tax, discount, notes, paid), `customer.*` | `invoice.lines` |
| `sample_letter` | `customer.*`, `sender.*`, `account.*` (since, open invoices, balance) | |
| `sample_order` | `order.*` (number, placed at, shipping, total), `customer.*` | `order.items` |
| `sample_certificate` | `employee.*`, `manager.*` | |

**Six templates** (slugs start with `sample-`):

| Slug | Type | Shows |
|---|---|---|
| `sample-invoice-standard` | `sample_invoice` (default) | repeated table rows, row numbers, a discount condition, all four formats |
| `sample-invoice-modern` | `sample_invoice` | another theme, date patterns, currency codes |
| `sample-invoice-hebrew` | `sample_invoice` | right-to-left, locale `he_IL`, a Hebrew page footer |
| `sample-welcome-letter` | `sample_letter` (default) | today's date, a list, a condition on open invoices |
| `sample-order-confirmation` | `sample_order` (default) | a repeat *section*, text case, HTML and TXT for email |
| `sample-employment-certificate` | `sample_certificate` (default) | conditions for current and former employees |

**Seven blocks**: `sample-company-letterhead`, `sample-page-footer`,
`sample-page-footer-he`, `sample-customer-details` (shared by three types),
`sample-bank-details`, `sample-payment-terms` (contains the bank details
block) and `sample-signature`.

**Ten constants**: `company_name`, `company_address`, `company_phone`,
`company_email`, `website_url`, `support_email`, `vat_number`, `bank_name`,
`bank_iban` and `bank_bic`. A constant is created only when its key does not
exist yet, so your own values are never overwritten.

### Use them

**Look at them.** In **Admin → Document templates**, click a preview link
(HTML, PDF, DOCX…). The document is filled with the sample values declared in
the sample types.

**Make them yours.** Edit the constants under **Admin → Constants** and
reload a preview: your company name, address and bank details now appear in
all six templates. Edit the *Sample: Company letterhead* block to change the
header everywhere.

**Change a template.** Open one in the editor, click a chip to change its
format, type `{{` to insert a field, and press **Preview**. To experiment
without touching the original, select it in the list and run the action
**Duplicate selected templates**.

**Render your own data.** Pass a dict shaped like the type's schema:

```python
import datetime as dt
from decimal import Decimal
from templates_pro.services import render, render_to_response

data = {
    "invoice": {
        "number": "INV-1001",
        "date": dt.date(2026, 3, 2),
        "due_date": dt.date(2026, 4, 1),
        "paid": False,
        "subtotal": Decimal("400.00"),
        "discount": Decimal("0"),
        "discount_amount": Decimal("0"),
        "tax_rate": Decimal("0.20"),
        "tax": Decimal("80.00"),
        "total": Decimal("480.00"),
        "notes": "",
        "lines": [
            {"description": "Consulting", "quantity": Decimal("4"),
             "unit_price": Decimal("100.00"), "amount": Decimal("400.00")},
        ],
    },
    "customer": {"name": "Dana Levi", "company": "Levi Ltd", "email": "dana@levi.example",
                 "address": "1 Main Street", "city": "Leeds", "country": "United Kingdom",
                 "vat_id": ""},
}

pdf = render("sample_invoice", data=data, fmt="pdf")          # the type's default template
pdf.content, pdf.filename                                      # bytes, "invoice-INV-1001.pdf"

# in a view:
return render_to_response("sample-invoice-modern", data=data, fmt="pdf")
```

Keys you leave out render as empty. To see the full shape of a type, print
its sample data:

```python
from templates_pro.registry import get_type
get_type("sample_order").sample_context()
```

**Start your own type from one.** Copy a class from
`templates_pro/samples/doctemplate_types.py` into your app's
`doctemplate_types.py`, give it your own `key`, and add a `build_context()`
that fills the same shape from your models
([template-types.md](template-types.md#build_context)). Then create a
template of your new type and paste a sample's content into it, or load the
HTML file directly ([below](#the-sample-html-files)). A template cannot be
moved to another type from the admin unless that type has the same fields.

### Reset or remove them

```bash
python manage.py templates_pro_samples --overwrite   # put sample blocks and templates back to the shipped version
python manage.py templates_pro_samples --remove      # delete sample templates and blocks
```

`--remove` keeps the constants, and keeps any sample block that your own
templates still use. Afterwards, take `"templates_pro.samples"` out of
`INSTALLED_APPS`; while sample templates exist, keep the app installed, or
their type shows as *unregistered*.

## Demo project

A complete Django project in `example/`, with models, real records and pages
outside the admin. It ships in the pip package too, so you can run it without
cloning the repository.

### Run it

**After `pip install django-templates-pro`**, from any folder:

```bash
python -m templates_pro.demo                    # or: templates-pro-demo
python -m templates_pro.demo --dir mydemo 8001  # another folder; other arguments go to runserver
```

The first run copies the demo project into `./templates-pro-demo`, with its own
SQLite database and a copy of this documentation for its `/docs/` page. Later
runs reuse that folder; delete it to start again. Your own project and its
database are never touched.

**From a clone of the repository**, from the repository root (or give the
script's path from anywhere):

```bash
python example/run_demo.py    # extra arguments go to runserver, e.g. 8001
```

It creates `.venv` in the repository root when no virtual environment is
active, installs the package when it is missing, runs `migrate`, runs
`seed_demo` when the database has no templates yet, and starts `runserver`.
It never re-seeds an existing database, so your edits to the demo are kept.

The same steps by hand, in an active virtual environment:

```bash
pip install -e .              # from the repository root
cd example
python manage.py migrate
python manage.py seed_demo    # content, records and the login admin / admin
python manage.py runserver
```

### Pages

| Page | What it shows |
|---|---|
| `/` | every template, with links that render it for real records in each enabled format |
| `/doc/<slug>/<pk>.<fmt>` | one document, e.g. `/doc/invoice-standard/1.pdf` |
| `/editors/` | the editor widget in every preset and skin, plus a custom toolbar (login required) |
| `/my-letter/` | a page where a non-admin user writes a template and renders it for a chosen customer (login required) |
| `/docs/` | this documentation, rendered from the repository's Markdown files |
| `/admin/` | templates, blocks, constants, generated documents, and the demo's own records |

### The demo records

| Customer | Locale | Has |
|---|---|---|
| Roe & Partners Ltd (Jane Roe) | `en_GB` | two GBP invoices (one with a 5% discount), an order |
| Becker Möbel GmbH | `de_DE` | a paid EUR invoice, an order |
| Amélie Durand | `fr_FR` | a EUR invoice, no company name, no VAT ID |
| כהן ושות' בע"מ (יעל כהן) | `he_IL` | an ILS invoice with a 10% discount |

There are also two employees: one current, one who has left.

### What each template demonstrates

Open these from `/`:

| Template | Open it for | Look at |
|---|---|---|
| `invoice-standard` | Roe & Partners, invoice 0041 | the line table (one repeated row), row numbers, the discount line that only this invoice has, the page footer with page X of Y in PDF |
| `invoice-standard` | Becker Möbel | German dates and number separators, EUR, the "Paid" wording from the `payment-terms` block |
| `invoice-standard` | Amélie Durand | the VAT ID line disappears (a condition inside the `customer-details` block) |
| `invoice-modern` | any invoice | a different theme, custom date patterns, currency shown as a code |
| `invoice-hebrew` | כהן ושות' | right-to-left layout in HTML, PDF and DOCX, Hebrew month names, ₪ |
| `invoice-hebrew` | an English customer | each paragraph following the direction of its own text |
| `welcome-letter` | any customer | today's date, the open-invoices paragraph (a condition), the sender passed in by the view (`sender=request.user`) |
| `order-confirmation` | an order | a repeat *section* instead of a table row; open the TXT format to see the plain-text version for email |
| `employment-certificate` | each employee | different wording for a current and a former employee; the project's own theme (`northwind`) |

### Things to try

1. **A block is shared.** Edit **Admin → Blocks → Company letterhead**, save,
   and reload any document from `/`. Every template changed.
2. **A constant is shared.** Change `company_name` under **Admin →
   Constants** and reload.
3. **Formatting.** Open *Invoice (standard)* in the admin, click the invoice
   date chip, choose another style, and press **Preview**.
4. **Insert a field.** Type `{{` in the editor and search for "VAT".
5. **Direction.** In *Invoice (Hebrew, RTL)*, change *Text direction* and
   watch the editor flip.
6. **A user-facing editor.** On `/my-letter/`, write a letter, pick a
   customer and press **Save & render**.
7. **Validation.** In `example/demo/doctemplate_types.py`, rename a field of
   a schema, restart, and run `python manage.py templates_pro_validate` to
   see which templates and blocks it breaks.

### Start again

```bash
python manage.py seed_demo --reset    # deletes ALL templates, blocks, constants and demo records, then reloads
```

Without `--reset`, `seed_demo` puts the demo's own templates, blocks and
constants back to their shipped content and leaves everything else alone.

How the pages get their data, and what is in each file, is in the
[demo README](../example/README.md).

## The sample HTML files

Both sets keep their content as files in the exact form the editor stores:

| Folder | Content |
|---|---|
| `example/demo/samples/` | `manifest.json`, `blocks/*.html`, `templates/*.html` (the demo) |
| `src/templates_pro/samples/content/` | the same, with `sample-` slugs and `sample_…` type keys (the packaged samples) |

`manifest.json` lists the constants, the blocks (in dependency order) and the
templates with their settings (type, theme, formats, footer block, locale,
direction, margins).

**As a reference.** Read a file next to
[html-contract.md](html-contract.md) to see how a chip, a repeated row or a
condition is written.

**As content for your own template.** Load a file into a template in a shell
or a data migration:

```python
from pathlib import Path
import templates_pro.samples
from templates_pro.models import DocumentTemplate

html = (Path(templates_pro.samples.__file__).parent
        / "content/templates/sample-welcome-letter.html").read_text(encoding="utf-8")

tpl = DocumentTemplate(name="Welcome", slug="welcome", template_type="customer_letter",  # your type
                       body=html, output_formats=["html", "pdf"])
tpl.full_clean()      # reports fields or blocks your type does not have
tpl.save()
```

The sample templates include the sample blocks (`sample-company-letterhead`
and others), so load the samples first, or remove those blocks from the
content.

**To check markup you generate yourself:**

```python
from templates_pro.core.compiler import compile_html
from templates_pro.registry import get_type

result = compile_html(html, schema=get_type("customer_letter").schema)
result.errors, result.warnings, result.variables
```

## Code examples

| For | Look at |
|---|---|
| a minimal type and view | [quickstart.md](quickstart.md) |
| types with several models, shared groups, locale and currency hooks | `example/demo/doctemplate_types.py` |
| a view that renders any template for an object | `document` in `example/demo/views.py` |
| the editor in your own form, with server-side validation | `LetterForm` and `user_letter` in `example/demo/views.py` |
| every preset, skin and a custom toolbar | `GalleryForm` in `example/demo/views.py` |
| constants computed in code | `example/demo/constants.py` |
| a project theme (CSS and Typst style) | `THEMES` in `example/exampleproject/settings.py`, `example/demo/static/demo/northwind-theme.css` |
| loading templates and blocks from files | `example/demo/management/commands/seed_demo.py` |
| the smallest possible types (dict contexts) | `tests/testapp/doctemplate_types.py` |
| email, background tasks, stored documents | [rendering.md](rendering.md#examples) |
