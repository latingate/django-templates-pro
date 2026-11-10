# Installation

## Requirements

- Python 3.10+
- Django 4.2+ (tested on 4.2 LTS, 5.0, 5.1 and 5.2)
- `django.contrib.contenttypes` (used by the GeneratedDocument model) and
  `django.contrib.staticfiles` (serves the editor bundle and themes)

## Install the package

```bash
pip install django-templates-pro              # HTML + TXT output
pip install "django-templates-pro[pdf]"       # + PDF (WeasyPrint)
pip install "django-templates-pro[docx]"      # + Word (python-docx)
pip install "django-templates-pro[all]"       # everything
```

From a private Git repository:

```bash
pip install "django-templates-pro[all] @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.1.0"
```

### WeasyPrint system libraries

WeasyPrint needs Pango (and HarfBuzz) from the OS:

| OS | Command |
|---|---|
| Debian / Ubuntu | `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` |
| Alpine | `apk add pango` |
| macOS | `brew install pango` |
| Windows | follow the WeasyPrint documentation (MSYS2) |

If the libraries are missing, `manage.py check` reports `templates_pro.W001`
and PDF rendering raises `RendererUnavailable`. Everything else keeps working.

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
python manage.py check          # reports missing optional libraries, unknown themes...
```

The admin is registered automatically: **Document templates**, **Blocks**,
**Constants** and **Generated documents**.

## Upgrading

See [operations.md](operations.md#upgrading).
