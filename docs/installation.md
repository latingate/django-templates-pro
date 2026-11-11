# Installation

## Requirements

- Python 3.10+
- Django 4.2+ (tested on 4.2 LTS, 5.0, 5.1 and 5.2)
- `django.contrib.contenttypes` (used by the GeneratedDocument model) and
  `django.contrib.staticfiles` (serves the editor bundle and themes)

## Install the package

```bash
pip install django-templates-pro
```

That's all: HTML, **PDF**, DOCX and TXT output work right away, on Windows,
macOS and Linux. Every dependency ships as a wheel, so no system libraries are
needed:

| Package | For |
|---|---|
| Django, Jinja2, Babel, html2text | core, formatting, TXT |
| `typst` | PDF (the Typst compiler is bundled in the wheel) |
| `python-docx` | DOCX |

Fonts with Latin and Hebrew characters (Noto Sans, Noto Sans Hebrew) are
bundled in the package. Typst also bundles Libertinus Serif. So Hebrew and
other right-to-left documents render correctly even on a bare server.

From a private Git repository:

```bash
pip install "django-templates-pro @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.2.0"
```

The extras `[pdf]`, `[docx]` and `[all]` from 0.1 still work, but they no
longer add anything: PDF and DOCX are always included.

### Optional: WeasyPrint as the PDF engine

The default PDF engine is Typst. If you need full CSS layout in PDFs, you can
switch to WeasyPrint instead. That engine needs the Pango system library:

```bash
pip install "django-templates-pro[weasyprint]"
```

| OS | System library |
|---|---|
| Debian / Ubuntu | `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` |
| macOS | `brew install pango` |
| Windows | MSYS2: `pacman -S mingw-w64-x86_64-pango`, then set `WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin` |

```python
TEMPLATES_PRO = {"PDF_ENGINE": "weasyprint"}
```

If Pango is missing, `manage.py check` reports `templates_pro.W001`. See
[rendering.md](rendering.md#pdf-engines) to choose between the engines.

## Configure Django

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "templates_pro",
]

# Optional; see settings.md for everything.
TEMPLATES_PRO = {
    "DEFAULT_CURRENCY": "EUR",
    "OUTPUT_FORMATS": ["html", "pdf", "docx", "txt"],
}
```

Add the preview URLs. The editor's **Preview** button and the admin's preview
links use them:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("templates-pro/", include("templates_pro.urls")),
]
```

Then:

```bash
python manage.py migrate
python manage.py check          # reports unknown themes, misconfigured engines...
```

The admin is registered automatically: **Document templates**, **Blocks**,
**Constants** and **Generated documents**.

A new install has no content. To get ready-made templates, blocks and
constants, add `"templates_pro.samples"` to `INSTALLED_APPS` and run
`python manage.py templates_pro_samples`; see
[quickstart.md](quickstart.md#start-from-the-samples-optional).

## Upgrading

See [operations.md](operations.md#upgrading).
