# django-templates-pro: setup guide

A complete, step-by-step guide to getting the repository running locally, the
demo working, PDF output enabled, and the package used in your other Django
projects. Commands are shown for **Windows (PowerShell)** first, with
macOS/Linux equivalents where they differ.

Steps you've already done are marked ✅. If you're redoing a setup from scratch,
just follow every step in order.

---

## Contents

1. [Prerequisites](#1-prerequisites)
2. [Get the code](#2-get-the-code-) ✅
3. [Create a virtual environment](#3-create-a-virtual-environment-) ✅
4. [Install Python dependencies](#4-install-python-dependencies-) ✅
5. [PDF output (nothing to install)](#5-pdf-output-nothing-to-install)
6. [Set up the demo database](#6-set-up-the-demo-database--after-the-fix) ✅ (after the fix)
7. [Run the demo](#7-run-the-demo)
8. [PyCharm configuration](#8-pycharm-configuration) (interpreter, Django support, run configurations)
9. [Verify everything](#9-verify-everything)
10. [Put the repository under Git](#10-put-the-repository-under-git)
11. [Use the package in your other Django projects](#11-use-the-package-in-your-other-django-projects)
12. [Production notes](#12-production-notes)
13. [Working on the editor (optional: Node / TipTap)](#13-working-on-the-editor-optional-node--tiptap)
14. [Continuing with Claude Code CLI](#14-continuing-with-claude-code-cli)
15. [Troubleshooting](#15-troubleshooting)
16. [Quick reference](#16-quick-reference)

---

## 1. Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.10 or newer (you have 3.13.5) | everything |
| pip | comes with Python | installing packages |
| Git | any recent | version control (section 10) |
| Node.js | 20 or newer | **only** if you change the editor (section 13) |

You do **not** need to install TipTap, Jinja2, or anything JavaScript to use
the package or run the demo:

- **Jinja2** (and Django, Babel, html2text, Typst for PDF, python-docx) are
  installed by `requirements.txt`. All of them are pip wheels: **no system
  libraries** (no MSYS2, Pango or GTK) are needed on any OS.
- **TipTap** is already compiled into the editor bundle shipped in
  `src/templates_pro/static/templates_pro/editor/` and served as normal Django
  static files.

## 2. Get the code ✅

Unzip `django-templates-pro.zip`, for example to:

```
C:\Users\<you>\PycharmProjects\django-templates-pro
```

The folder that contains `pyproject.toml` is the **repo root**. All commands
below start from there unless they say otherwise.

```
django-templates-pro/
├── pyproject.toml          ← repo root
├── requirements.txt
├── requirements-dev.txt
├── src/templates_pro/      ← the package
├── example/                ← demo project (manage.py is here)
├── frontend/               ← editor source (only for editor changes)
├── tests/
└── docs/
```

## 3. Create a virtual environment ✅

**Windows (PowerShell):**

```powershell
cd C:\Users\<you>\PycharmProjects\django-templates-pro
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell refuses to run the activate script ("running scripts is disabled"),
allow local scripts once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**macOS / Linux:**

```bash
cd ~/projects/django-templates-pro
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should now start with `(.venv)`.

**Recommended on Windows:** make Python use UTF-8 everywhere. This prevents
`UnicodeDecodeError` problems like the one fixed in section 15, in any project:

```powershell
setx PYTHONUTF8 1
```

Open a new terminal (and restart PyCharm) afterwards.

## 4. Install Python dependencies ✅

From the **repo root**, with the venv active:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

- The file name uses a **hyphen**: `requirements-dev.txt` (not `requirements.dev.txt`).
- Run it **from the repo root**. The file contains `-e .`, which installs the
  package in editable mode from the current folder.
- `requirements-dev.txt` = `requirements.txt` (runtime) + the package itself
  (editable) + pytest, pytest-django, nox, ruff.

Check what got installed:

```powershell
python -m pip show django jinja2 babel typst python-docx
```

## 5. PDF output (nothing to install)

PDFs are made by **Typst**, whose compiler comes inside the `typst` pip
package, with fonts for Latin and Hebrew bundled in this package. PDF output
therefore works right after step 4, with right-to-left (Hebrew) support,
tables included.

> **If you followed the earlier version of this guide** and installed MSYS2 +
> Pango and set `WEASYPRINT_DLL_DIRECTORIES`: that was only for WeasyPrint,
> which is now optional. You can leave it (harmless) or remove it:
> uninstall MSYS2, then run `setx WEASYPRINT_DLL_DIRECTORIES ""` and restart
> PyCharm. Also `python -m pip uninstall weasyprint` if it is still in your venv.

### Optional: WeasyPrint engine (full CSS PDFs)

Only if you specifically want PDFs laid out from CSS. It needs the Pango
system library:

1. `python -m pip install weasyprint`
2. Pango:
   - **Windows:** install MSYS2 (<https://www.msys2.org>), then in the **MSYS2
     MINGW64** shell run `pacman -S mingw-w64-x86_64-pango`, then in PowerShell
     `setx WEASYPRINT_DLL_DIRECTORIES "C:\msys64\mingw64\bin"`, and restart the
     terminal and PyCharm.
   - **macOS:** `brew install pango`
   - **Ubuntu / Debian:** `sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`
3. In settings: `TEMPLATES_PRO = {"PDF_ENGINE": "weasyprint", ...}`

## 6. Set up the demo database ✅ (after the fix)

The demo uses SQLite at `example\db.sqlite3`. It must be created **once**
before running the server. Running only `runserver` gives
`no such table: templates_pro_documenttemplate`.

```powershell
cd example
python manage.py migrate
python manage.py seed_demo
```

- `migrate` creates all tables.
- `seed_demo` loads 10 constants, 7 shared blocks, 6 templates (one of them a
  Hebrew right-to-left invoice), sample customers, invoices, orders and
  employees, and creates the login **admin / admin** (demo only).

> If `seed_demo` failed with `UnicodeDecodeError: 'charmap' codec can't decode…`,
> you have the old `seed_demo.py`. Replace `example\demo\management\commands\seed_demo.py`
> and `example\demo\views.py` with the fixed versions (or use the latest zip).
> The command is safe to re-run.

Useful variants:

```powershell
python manage.py seed_demo --reset     # wipe demo content and reload it
python manage.py showmigrations templates_pro demo   # every line should be [X]
```

## 7. Run the demo

```powershell
cd example          # if not already there
python manage.py runserver
```

| URL | What you'll see |
|---|---|
| <http://127.0.0.1:8000/> | every template rendered for real records, in each enabled format |
| <http://127.0.0.1:8000/editors/> | the editor in all presets and skins, outside the admin |
| <http://127.0.0.1:8000/my-letter/> | a user-facing page where a user writes and renders a template |
| <http://127.0.0.1:8000/docs/> | the documentation (every `.md` file of the repository), in reading order |
| <http://127.0.0.1:8000/admin/> | Document templates, Blocks, Constants, Generated documents (login admin / admin) |

Things to try:

- Edit **Admin → Blocks → Company letterhead**, save, and reload `/`. Every
  template using it changes.
- Open a template and type `{{` in the editor to insert a field. Click a chip
  to change its format.
- Click **Preview** in the editor toolbar.
- Open the German customer's invoice (Becker Möbel GmbH) to see `de_DE` dates
  and EUR.
- Open **Invoice (Hebrew, RTL)** for the customer כהן ושות' in PDF, DOCX and
  HTML. In the admin, change its *Text direction* field and watch the editor
  flip.

## 8. PyCharm configuration

### 8.1 Interpreter

**Settings → Project → Python Interpreter → Add Interpreter → Existing** →
`C:\Users\<you>\PycharmProjects\django-templates-pro\.venv\Scripts\python.exe`

### 8.2 Mark source folders (imports and autocomplete)

Right-click `src` → **Mark Directory as → Sources Root**.
Right-click `example` → **Mark Directory as → Sources Root**.

### 8.3 Django support (if your PyCharm has *Languages & Frameworks → Django*)

**Settings → Languages & Frameworks → Django**

| Field | Value |
|---|---|
| Enable Django Support | ✔ |
| Django project root | `C:\Users\<you>\PycharmProjects\django-templates-pro\example` |
| Settings | `exampleproject\settings.py` |
| Manage script | `manage.py` |
| Do not use Django test runner | ✔ (the tests use pytest) |
| Environment variables | leave empty |
| Folder pattern to track files | leave the default |

The project root is the `example` folder (it contains `manage.py`), **not**
the repo root. Settings and the manage script are relative to it.

Then:

- **Settings → Languages & Frameworks → Template Languages** → Template language: **Django**.
- **Settings → Tools → Python Integrated Tools** → Default test runner: **pytest**.

Run configuration: **Run → Edit Configurations → + → Django Server**

| Field | Value |
|---|---|
| Host / Port | `127.0.0.1` / `8000` |
| Python interpreter | the project `.venv` |
| Working directory | `…\django-templates-pro\example` |
| Environment variables | `PYTHONUNBUFFERED=1;DJANGO_SETTINGS_MODULE=exampleproject.settings` |

Optional extra: `PYTHONUTF8=1`, if you didn't set it globally with `setx`.

`manage.py` tasks (`migrate`, `seed_demo`, `templates_pro_validate`) are then
available under **Tools → Run manage.py Task…** (Ctrl+Alt+R).

### 8.4 Without Django support: plain Python run configurations

Create these under **Run → Edit Configurations → + → Python**:

| Name | Script path | Parameters | Working directory |
|---|---|---|---|
| Demo: runserver | `…\example\manage.py` | `runserver` | `…\example` |
| Demo: migrate | `…\example\manage.py` | `migrate` | `…\example` |
| Demo: seed | `…\example\manage.py` | `seed_demo` | `…\example` |
| Tests | *(Module name)* `pytest` | *(empty)* | repo root |

For the **Tests** configuration, switch "Script path" to **Module name** and
enter `pytest`.

### 8.5 Run tests from PyCharm

The repo root's `pyproject.toml` already tells pytest which settings to use
(`tests.settings`). Create a pytest run configuration with the **working
directory = repo root**, or right-click the `tests` folder → **Run 'pytest in
tests'**.

If you set `PYTHONUTF8` with `setx`, PyCharm sees it only after a restart.
You can also add it per configuration under **Environment variables**.

## 9. Verify everything

From the **repo root**:

```powershell
pytest
```

Expected: **144 passed** (no system libraries needed; PDF tests use Typst).

From `example\`:

```powershell
python manage.py check                    # "System check identified no issues"
python manage.py templates_pro_validate   # "All templates and blocks are valid."
```

Optional, from the repo root:

```powershell
ruff check .        # lint: "All checks passed!"
```

## 10. Put the repository under Git

The repo already has a `.gitignore`, which excludes the venv, `node_modules`,
the demo database and media. It deliberately **keeps** the built editor bundle.

```powershell
cd C:\Users\<you>\PycharmProjects\django-templates-pro
git init
git add .
git commit -m "django-templates-pro 0.1.0"
git branch -M main
```

Push to a **private** GitHub repository (create an empty one on github.com first):

```powershell
git remote add origin git@github.com:<you>/django-templates-pro.git
git push -u origin main
git tag v0.1.0
git push --tags
```

Before pushing, update the placeholder URLs in `pyproject.toml`
(`[project.urls]`, currently `github.com/peltransport/...`) to your real
repository.

The included GitHub Actions workflow (`.github/workflows/ci.yml`) runs the
tests on Python 3.10–3.13 × Django 4.2 / 5.1 / 5.2, builds the editor bundle,
and lints on every push.

## 11. Use the package in your other Django projects

Do **not** copy `requirements*.txt` into other projects. Install the package
itself, inside **that project's** virtual environment.

### 11.1 Install

While you are still developing the package (changes apply immediately):

```powershell
python -m pip install -e "C:\Users\<you>\PycharmProjects\django-templates-pro"
```

Once it's on GitHub (a fixed, tagged version):

```powershell
python -m pip install "django-templates-pro @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.2.0"
```

In that project's own `requirements.txt`, add the same line, for example:

```
django-templates-pro @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.2.0
```

That one package brings HTML, PDF, DOCX and TXT output. The only extra is
`[weasyprint]`, for the optional WeasyPrint PDF engine.

### 11.2 Settings

```python
INSTALLED_APPS = [
    # ...
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "templates_pro",
]

TEMPLATES_PRO = {
    "DEFAULT_CURRENCY": "ILS",          # your default
    "DEFAULT_LOCALE": "he_IL",          # or leave out to use LANGUAGE_CODE; he_* = RTL by default
    "OUTPUT_FORMATS": ["html", "pdf", "docx", "txt"],
}
```

All options are listed in `docs/settings.md`.

### 11.3 URLs (needed for the editor's Preview button)

```python
# project urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("templates-pro/", include("templates_pro.urls")),
]
```

### 11.4 Database

```powershell
python manage.py migrate
```

### 11.5 Declare template types

Create `doctemplate_types.py` in any app of that project. It is
auto-discovered. Minimal example:

```python
# billing/doctemplate_types.py
from templates_pro import register, TemplateType, Var, Group, ListOf


@register
class InvoiceTemplate(TemplateType):
    key = "invoice"                       # never change once templates exist
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
        # Plain data only: dicts, lists, str, numbers, Decimal, bool, None, dates.
        return {"invoice": {
            "number": invoice.number,
            "date": invoice.date,
            "total": invoice.total,
            "lines": [{"description": l.description, "amount": l.amount}
                      for l in invoice.lines.all()],
        }}
```

See `docs/template-types.md` for locale/currency hooks and sample data, and
`example/demo/doctemplate_types.py` for four complete examples.

### 11.6 Render documents

```python
from templates_pro.services import render_to_response

def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render_to_response("invoice", invoice, fmt="pdf")
```

More in `docs/rendering.md`: emails, storing issued documents with
`generate()`, and custom renderers.

### 11.7 Check

```powershell
python manage.py check
python manage.py templates_pro_validate
```

## 12. Production notes

- **Static files:** run `python manage.py collectstatic` on every deploy. The
  editor bundle changes between package versions.
- **No system packages for PDF:** the default Typst engine needs nothing on
  the server, including slim Docker images.
- **Fonts:** Typst PDFs use the bundled fonts (Noto Sans, Noto Sans Hebrew,
  Libertinus Serif). For brand fonts, add a folder with `TYPST_FONT_PATHS` and
  name them in your theme's `"typst"` style. Set `TYPST_IGNORE_SYSTEM_FONTS:
  True` for identical output on every machine.
- **Cache:** use a shared cache (Redis or Memcached) so that block and
  constant edits are seen by all workers immediately. It is correct without
  one, just slightly slower.
- **Permissions:** give template editors `change_documenttemplate` and
  `change_templateblock`. The preview endpoints require
  `PREVIEW_PERMISSION` (see `docs/settings.md`).
- **Remote images:** remote image URLs in PDF/DOCX are blocked unless they are
  listed in `ALLOWED_URL_PREFIXES`. Images from your own static or media
  files always work.
- **Large batches:** render PDFs in a background task (Celery, RQ) rather than
  in the request.
- **Upgrades:** `pip install -U …`, then `migrate`, `collectstatic` and
  `templates_pro_validate` (see `docs/operations.md`).
- Never use the demo's `admin/admin` account or `SECRET_KEY` anywhere real.

## 13. Working on the editor (optional: Node / TipTap)

Only needed if you change the editor's toolbar, custom nodes or styles in
`frontend/src/`.

1. Install **Node.js 20+** (LTS) from <https://nodejs.org>.
2. Build:

   ```powershell
   cd frontend
   npm install          # downloads TipTap, Vite... into frontend\node_modules
   npm run build        # writes src\templates_pro\static\templates_pro\editor\
   ```

3. While developing: `npm run watch` rebuilds on every save. Reload the demo
   page to see the changes.
4. If you changed how nodes are written to HTML (`extensions.js`), also run:

   ```powershell
   npm run contract          # regenerates tests\fixtures\editor_roundtrip\
   cd ..
   pytest tests\test_contract.py
   ```

5. Commit the rebuilt bundle together with the source change.

## 14. Continuing with Claude Code CLI

The repo includes `CLAUDE.md`, which Claude Code reads automatically. It
describes the architecture, the rules that must not be broken (sandbox,
plain-data contexts, the HTML contract), commands and conventions.

```powershell
cd C:\Users\<you>\PycharmProjects\django-templates-pro
claude
```

A good first task is to integrate the package into one of your real projects
(section 11) and write a template type for one of its models.

## 15. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ERROR: Could not open requirements file: requirements.dev.txt` | wrong file name | use `requirements-dev.txt` (hyphen) |
| `-e .` installs the wrong thing / "does not appear to be a Python project" | ran pip outside the repo root | `cd` to the folder with `pyproject.toml` first |
| `OperationalError: no such table: templates_pro_documenttemplate` | migrations not applied | `cd example`, then `python manage.py migrate` and `python manage.py seed_demo` (section 6) |
| `UnicodeDecodeError: 'charmap' codec can't decode byte…` in `seed_demo` | old `seed_demo.py` read files with the Windows code page | use the fixed `seed_demo.py` / `views.py` (latest zip); optionally `setx PYTHONUTF8 1` |
| `WeasyPrint could not import some external libraries` / `templates_pro.W001` | `PDF_ENGINE` is `"weasyprint"` but Pango is missing | remove `PDF_ENGINE` (default Typst), or install Pango (section 5, optional part) |
| Hebrew document comes out left-to-right | locale not Hebrew and direction *Auto* | set the template's *Text direction* to *Right to left*, or its *Locale* to `he_IL` |
| An English line in a Hebrew document is left-aligned | each paragraph follows its first letter (intended) | start the paragraph with Hebrew text, or align it explicitly with the toolbar |
| Custom theme looks plain in PDF | project theme has no Typst style | add a `"typst"` entry to the theme (see `docs/rendering.md#themes`) |
| `.venv\Scripts\Activate.ps1 cannot be loaded… running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Editor doesn't appear (plain textarea or nothing) | static files not found | in the demo: check `DEBUG = True`; in production: run `collectstatic`; make sure `{{ form.media }}` is in your page's `<head>` |
| Preview button missing | `templates_pro.urls` not included | add `path("templates-pro/", include("templates_pro.urls"))` |
| Preview returns 403 | user lacks `PREVIEW_PERMISSION` | grant `templates_pro.change_documenttemplate` or change the setting |
| Saving a template: "unknown variable '…'" | the field isn't in the type's schema (renamed or removed) | add it to the schema, or remove the red chip; run `templates_pro_validate` |
| `Template type 'x' is not registered` | the app with `doctemplate_types.py` isn't in `INSTALLED_APPS`, or the file has an import error | check `INSTALLED_APPS`; run `python -c "import yourapp.doctemplate_types"` |
| `UnsafeContextError: context.invoice is a …Model` | `build_context()` returned a model instance | convert to dicts/values in `build_context()` |
| Images missing in PDF/DOCX | URL not allowed by the safe fetcher | use `/static/…` or `/media/…` paths, or add the host to `ALLOWED_URL_PREFIXES` |
| Wrong currency or date format | locale/currency precedence | see `docs/template-types.md#locale-and-currency-hooks` |

## 16. Quick reference

```powershell
# one-time setup (repo root)
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt

# demo (example folder)
cd example
python manage.py migrate
python manage.py seed_demo            # --reset to reload
python manage.py runserver            # http://127.0.0.1:8000  admin / admin

# checks
pytest                                # repo root, expect 144 passed
python manage.py check                # example folder
python manage.py templates_pro_validate
ruff check .                          # repo root

# editor (only when changing frontend/src)
cd frontend
npm install
npm run build
npm run contract
```

Further reading: `README.md` and `docs/` (installation, quickstart, concepts,
template types, formatting, editor, rendering, security, settings, operations,
HTML contract, development).
