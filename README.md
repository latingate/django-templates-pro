# django-templates-pro

WYSIWYG document templates for Django. Admins and users write templates in a
rich-text editor (TipTap). The templates can contain:

- **variables** (invoice number, customer name…), declared per *template type* in code
- **constants** (website name, company address…), edited in the admin
- **dynamic values** (today, current time, year, row number, page X of Y)
- **formatting** for dates, times, numbers, money, percentages and text, chosen per chip
- **shared blocks** (header, footer, customer details…), edited once and used everywhere
- **repeat sections / repeated table rows** (invoice lines) and **conditions**
- **text direction** per template (auto from the locale, LTR or RTL), in the editor and every output

Templates render to **HTML, PDF (Typst), DOCX (python-docx) and TXT**, with
full **right-to-left** support (Hebrew, Arabic…). Everything installs with
pip alone: no system libraries, on Windows, macOS and Linux.

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
pip install django-templates-pro      # HTML, PDF, DOCX and TXT; nothing else to install
```

```python
INSTALLED_APPS = [..., "django.contrib.contenttypes", "django.contrib.staticfiles", "templates_pro"]
# urls.py — preview endpoints used by the editor
path("templates-pro/", include("templates_pro.urls")),
```

```bash
python manage.py migrate
```

Want something to look at first? Add `"templates_pro.samples"` to `INSTALLED_APPS` and run
`python manage.py templates_pro_samples`: six ready-made templates (one Hebrew, right-to-left),
seven shared blocks and constants appear in the admin, with working previews
([sample content](https://github.com/latingate/django-templates-pro/blob/master/docs/quickstart.md#start-from-the-samples-optional)).

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

Requirements: Python 3.10+ and Django 4.2+. That's all: PDF output uses the
`typst` wheel and bundled fonts (Latin + Hebrew). WeasyPrint is available as an
optional PDF engine ([rendering.md](https://github.com/latingate/django-templates-pro/blob/master/docs/rendering.md#pdf-engines)).

## Try the demo

After `pip install django-templates-pro`:

```bash
python -m templates_pro.demo      # http://127.0.0.1:8000  (admin / admin)
```

It copies the demo project into `./templates-pro-demo` (another folder: `--dir`),
migrates its own SQLite database, loads the demo content and starts the server. It
never touches your own project. Run the same command again to restart it.

From a clone of the repository, `python example/run_demo.py` does the same in place,
and also creates `.venv` and installs the package when needed. Details are in
[docs/samples.md](https://github.com/latingate/django-templates-pro/blob/master/docs/samples.md#run-it).

The demo has six templates (an English and a Hebrew right-to-left invoice, a
modern invoice, a letter, an order email and an HR certificate), seven shared
blocks (one of them nested), constants, document themes (one of them a
project theme), every editor preset and skin, and a user-facing editor page.
It also serves this documentation at <http://127.0.0.1:8000/docs/>.

## Documentation

The full list, in reading order, is in [docs/index.md](https://github.com/latingate/django-templates-pro/blob/master/docs/index.md).

| | |
|---|---|
| [**Setup guide**](https://github.com/latingate/django-templates-pro/blob/master/SETUP.md) | step-by-step local setup, demo, PyCharm, Windows PDF, troubleshooting |
| [Installation](https://github.com/latingate/django-templates-pro/blob/master/docs/installation.md) | requirements, settings, URLs, system libraries |
| [Quickstart](https://github.com/latingate/django-templates-pro/blob/master/docs/quickstart.md) | first template type, first template, first PDF |
| [Samples, demo and examples](https://github.com/latingate/django-templates-pro/blob/master/docs/samples.md) | the packaged samples, the demo project and the sample HTML files, and how to use them |
| [Concepts](https://github.com/latingate/django-templates-pro/blob/master/docs/concepts.md) | variables, constants, dynamic values, blocks, repeats, conditions |
| [Template types](https://github.com/latingate/django-templates-pro/blob/master/docs/template-types.md) | schemas, `build_context`, samples, locale & currency hooks |
| [Formatting](https://github.com/latingate/django-templates-pro/blob/master/docs/formatting.md) | how formatting works; date/number/money/text format reference |
| [The editor](https://github.com/latingate/django-templates-pro/blob/master/docs/editor.md) | widget options, presets, skins, toolbar, JS API, styling |
| [The admin](https://github.com/latingate/django-templates-pro/blob/master/docs/admin.md) | templates, blocks, constants, generated documents, previews, permissions |
| [Rendering](https://github.com/latingate/django-templates-pro/blob/master/docs/rendering.md) | services API, formats, themes, page setup, stored documents, custom renderers |
| [Security](https://github.com/latingate/django-templates-pro/blob/master/docs/security.md) | the sandbox, sanitising, URL fetching, permissions |
| [Settings](https://github.com/latingate/django-templates-pro/blob/master/docs/settings.md) | `TEMPLATES_PRO` reference |
| [Management commands](https://github.com/latingate/django-templates-pro/blob/master/docs/commands.md) | `templates_pro_validate`, `templates_pro_samples`, `seed_demo` |
| [Operations](https://github.com/latingate/django-templates-pro/blob/master/docs/operations.md) | schema changes, caching, migrations, upgrades |
| [Troubleshooting](https://github.com/latingate/django-templates-pro/blob/master/docs/troubleshooting.md) | symptoms, causes and fixes |
| [HTML contract](https://github.com/latingate/django-templates-pro/blob/master/docs/html-contract.md) | the chip markup shared by editor and compiler |
| [Development](https://github.com/latingate/django-templates-pro/blob/master/docs/development.md) | repo layout, tests, building the editor bundle |

## License

MIT
