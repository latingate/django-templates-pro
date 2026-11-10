# django-templates-pro

WYSIWYG document templates for Django. Admins and users write templates in a
rich-text editor (TipTap). The templates can contain:

- **variables** (invoice number, customer name…), declared per *template type* in code
- **constants** (website name, company address…), edited in the admin
- **dynamic values** (today, current time, year, row number, page X of Y)
- **formatting** for dates, times, numbers, money, percentages and text, chosen per chip
- **shared blocks** (header, footer, customer details…), edited once and used everywhere
- **repeat sections / repeated table rows** (invoice lines) and **conditions**

Templates render to **HTML, PDF (WeasyPrint), DOCX (python-docx) and TXT**.

Users never write template syntax. The editor stores HTML with chips, and the
package compiles it to **sandboxed Jinja2**. Contexts must be plain data, so
templates can't reach your models, the ORM or Python internals.

```python
from templates_pro.services import render_to_response

def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render_to_response("invoice", invoice, fmt="pdf")   # the type's default template
```

## Install

```bash
pip install "django-templates-pro[pdf,docx]"      # or just django-templates-pro for HTML/TXT
```

```python
INSTALLED_APPS = [..., "django.contrib.contenttypes", "django.contrib.staticfiles", "templates_pro"]
# urls.py — preview endpoints used by the editor
path("templates-pro/", include("templates_pro.urls")),
```

```bash
python manage.py migrate
```

Then declare what can be templated, in any app's `doctemplate_types.py`:

```python
from templates_pro import register, TemplateType, Var, Group, ListOf

@register
class InvoiceTemplate(TemplateType):
    key = "invoice"
    label = "Invoice"
    filename = "invoice-{invoice.number}"
    schema = {
        "invoice": Group("Invoice", {
            "number": Var("string", "Invoice number", sample="INV-0042"),
            "date": Var("date", "Date"),
            "total": Var("money", "Total"),
            "lines": ListOf("Line items", {
                "description": Var("string", "Description"),
                "amount": Var("money", "Amount"),
            }),
        }),
    }

    def build_context(self, invoice, **kwargs):
        return {"invoice": {
            "number": invoice.number, "date": invoice.date, "total": invoice.total,
            "lines": [{"description": l.description, "amount": l.amount} for l in invoice.lines.all()],
        }}
```

Open **Admin → Document templates**, pick the type, and write.

Requirements: Python 3.10+ and Django 4.2+. PDF output needs WeasyPrint and its system
libraries (Pango).

## Try the demo

```bash
cd example
python manage.py migrate && python manage.py seed_demo
python manage.py runserver        # http://127.0.0.1:8000  (admin / admin)
```

The demo has five templates (two invoices, a letter, an order email and an HR
certificate), six shared blocks (one of them nested), constants, four document
themes, every editor preset and skin, and a user-facing editor page.

## Documentation

| | |
|---|---|
| [Installation](docs/installation.md) | requirements, settings, URLs, system libraries |
| [Quickstart](docs/quickstart.md) | first template type, first template, first PDF |
| [Concepts](docs/concepts.md) | variables, constants, dynamic values, blocks, repeats, conditions |
| [Template types](docs/template-types.md) | schemas, `build_context`, samples, locale & currency hooks |
| [Formatting](docs/formatting.md) | date/number/money/text format reference |
| [The editor](docs/editor.md) | widget options, presets, skins, toolbar, JS API, styling |
| [Rendering](docs/rendering.md) | services API, formats, themes, page setup, stored documents, custom renderers |
| [Security](docs/security.md) | the sandbox, sanitising, URL fetching, permissions |
| [Settings](docs/settings.md) | `TEMPLATES_PRO` reference |
| [Operations](docs/operations.md) | validation command, caching, migrations, upgrades |
| [HTML contract](docs/html-contract.md) | the chip markup shared by editor and compiler |
| [Development](docs/development.md) | repo layout, tests, building the editor bundle |

## License

MIT
