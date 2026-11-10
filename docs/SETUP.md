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
2. [Get the code](#2-get-the-code) ✅
3. [Create a virtual environment](#3-create-a-virtual-environment) ✅
4. [Install Python dependencies](#4-install-python-dependencies) ✅
5. [Enable PDF output (Pango / WeasyPrint)](#5-enable-pdf-output-pango--weasyprint)
6. [Set up the demo database](#6-set-up-the-demo-database) ✅ (after the fix)
7. [Run the demo](#7-run-the-demo)
8. [PyCharm configuration](#8-pycharm-configuration)
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
| Pango (system library) | via MSYS2 on Windows | **PDF output only** (section 5) |
| Node.js | 20 or newer | **only** if you change the editor (section 13) |

You do **not** need to install TipTap, Jinja2, or anything JavaScript to use
the package or run the demo:

- **Jinja2** (and Django, Babel, html2text, WeasyPrint, python-docx) are
  installed by `requirements.txt`.
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
python -m pip show django jinja2 babel weasyprint python-docx
```

## 5. Enable PDF output (Pango / WeasyPrint)

WeasyPrint is a pip package, but it needs the **Pango** text-layout library
from the operating system. Without it you get this message (harmless for
everything except PDF):

```
WeasyPrint could not import some external libraries...
(templates_pro.W001) Output format 'pdf' is enabled but its library is not installed.
```

HTML, DOCX and TXT output work regardless. Only PDF needs this step.

### Windows

1. Install **MSYS2** from <https://www.msys2.org>, keeping the default
   location `C:\msys64`.
2. Open the **MSYS2 MINGW64** shell (from the Start menu) and run:

   ```bash
   pacman -S mingw-w64-x86_64-pango
   ```

   Answer `Y` when asked.
3. Tell WeasyPrint where the libraries are. In **PowerShell**:

   ```powershell
   setx WEASYPRINT_DLL_DIRECTORIES "C:\msys64\mingw64\bin"
   ```

4. **Close and reopen** the terminal and **restart PyCharm**. `setx` only
   affects new processes.
5. Test it (venv active):

   ```powershell
   python -m weasyprint --info
   ```

   This should print versions without the "could not import" message.

### macOS

```bash
brew install pango
```

### Ubuntu / Debian

```bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

### Don't need PDF yet?

Leave it. The warning is safe to ignore, and PDF links in the demo will show
an error page until Pango is installed. (Removing `"pdf"` from the demo
settings would make the seeded templates fail validation, so leaving it on is
simpler.)

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
- `seed_demo` loads 10 constants, 6 shared blocks, 5 templates, sample
  customers, invoices, orders and employees, and creates the login
  **admin / admin** (demo only).

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
| <http://127.0.0.1:8000/admin/> | Document templates, Blocks, Constants, Generated documents (login admin / admin) |

Things to try:

- Edit **Admin → Blocks → Company letterhead**, save, and reload `/`. Every
  template using it changes.
- Open a template and type `{{` in the editor to insert a field. Click a chip
  to change its format.
- Click **Preview** in the editor toolbar.
- Open the German customer's invoice (Becker Möbel GmbH) to see `de_DE` dates
  and EUR.

## 8. PyCharm configuration

Your PyCharm is the **Community** edition (no built-in Django support), so use
plain Python run configurations.

### Interpreter

**Settings → Project → Python Interpreter → Add Interpreter → Existing** →
`C:\Users\<you>\PycharmProjects\django-templates-pro\.venv\Scripts\python.exe`

### Mark source folders (better imports and autocomplete)

Right-click `src` → **Mark Directory as → Sources Root**.
Right-click `example` → **Mark Directory as → Sources Root**.

### Run configurations

Create these under **Run → Edit Configurations → + → Python**:

| Name | Script path | Parameters | Working directory |
|---|---|---|---|
| Demo: runserver | `…\example\manage.py` | `runserver` | `…\example` |
| Demo: migrate | `…\example\manage.py` | `migrate` | `…\example` |
| Demo: seed | `…\example\manage.py` | `seed_demo` | `…\example` |
| Tests | *(Module name)* `pytest` | *(empty)* | repo root |

For the **Tests** configuration, switch "Script path" to **Module name** and
enter `pytest`.

If you set `WEASYPRINT_DLL_DIRECTORIES` or `PYTHONUTF8` with `setx`, PyCharm
sees them only after a restart. You can also add them per configuration under
**Environment variables**.

## 9. Verify everything

From the **repo root**:

```powershell
pytest
```

Expected: **98 passed**. If Pango is not installed, PDF-related tests will
fail. Install Pango (section 5) to get the full pass.

From `example\`:

```powershell
python manage.py check                    # no errors; W001 only if Pango is missing
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
python -m pip install -e "C:\Users\<you>\PycharmProjects\django-templates-pro[all]"
```

Once it's on GitHub (a fixed, tagged version):

```powershell
python -m pip install "django-templates-pro[all] @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.1.0"
```

In that project's own `requirements.txt`, add the same line, for example:

```
django-templates-pro[all] @ git+ssh://git@github.com/<you>/django-templates-pro.git@v0.1.0
```

Extras: `[pdf]` = WeasyPrint, `[docx]` = python-docx, `[all]` = both. With no
extras you get HTML and TXT only.

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
    "DEFAULT_LOCALE": "en_US",          # or leave out to use LANGUAGE_CODE
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
- **Pango on the server:** install the Linux packages from section 5 in your
  server image or Dockerfile, for example
  `apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`.
- **Fonts:** PDFs use fonts installed on the server. Install the fonts your
  themes use, e.g. `fonts-dejavu` and a Hebrew font if you need one.
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
| `WeasyPrint could not import some external libraries` / `templates_pro.W001` | Pango not installed or not found | section 5; restart terminal/PyCharm after `setx` |
| PDF link shows "PDF output needs WeasyPrint…" | same as above | section 5 |
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
pytest                                # repo root, expect 98 passed
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
