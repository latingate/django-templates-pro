# CLAUDE.md — django-templates-pro

Reusable Django app (pip: `django-templates-pro`, import/app label: `templates_pro`).
WYSIWYG document templates: TipTap editor → stored HTML with "chips" → compiled to
sandboxed Jinja2 → rendered to HTML / PDF (Typst; WeasyPrint optional) / DOCX (python-docx) / TXT
(html2text), with right-to-left support. Used by several unrelated Django projects, so keep it
generic: no project-specific code here.

**Hard requirement: `pip install django-templates-pro` must be enough on Windows, macOS and Linux.**
No dependency may need system libraries (that's why WeasyPrint is only an optional engine). Check
any new dependency ships wheels for all three.

Support matrix: **Python 3.10+, Django 4.2+**. Don't use 3.11+ syntax/stdlib
(no `typing.Self`, `tomllib`, `ExceptionGroup`) or Django 5-only APIs (`db_default`,
`GeneratedField`, `Field.choices` callables in migrations). Every module has
`from __future__ import annotations`.

## Architecture (read before changing anything)

- `core/` is **pure Python, no Django imports**: `schema.py` (Var/Group/ListOf), `compiler.py`
  (HTML → Jinja + sanitiser; **the HTML contract**), `engine.py` (sandbox, plain-data check,
  limits), `formatting.py` (Babel, `direction_for`), `renderers/` (`typst_pdf.py` = default PDF,
  HTML→Typst converter `TypstWriter` + Typst themes; `pdf.py` = optional WeasyPrint; `docx.py`;
  `txt.py`; `html.py`).
- Django layer: `registry.py` (TemplateType/register; projects define types in
  `<app>/doctemplate_types.py`, autodiscovered in `apps.py`), `models.py`, `services.py`
  (public API), `widgets.py`, `forms.py`, `admin.py`, `views.py` (previews), `fetchers.py`,
  `themes.py`, `conf.py` (`settings.TEMPLATES_PRO` dict with defaults), `checks.py`, `signals.py`,
  `engines.py` (registers the PDF renderer chosen by `PDF_ENGINE`, at startup and on setting changes).
- `samples/`: optional app `templates_pro.samples` = starter content for pip users. Sample types
  (`sample_*` keys, dict contexts, no models) + `content/` (manifest, blocks, templates in
  stored-HTML form, `sample-` slugs, logo as a data URI) + `loader.py`; loaded by
  `manage.py templates_pro_samples`. It is an adapted copy of `example/demo/samples/`: when a
  demo sample changes, update the copy too.
- `fonts/`: bundled Noto Sans + Noto Sans Hebrew (OFL, keep `OFL.txt`), always on Typst's font path.
- `frontend/` = editor source (TipTap 3 + Vite, vanilla JS, no framework). The **built** bundle
  is committed in `src/templates_pro/static/templates_pro/editor/`. Consumers never need Node.
- `example/` = demo project; `example/demo/samples/` = sample templates/blocks in stored-HTML form.

## Invariants — do not break

1. **Users never author Jinja.** Only `compiler.py` emits template syntax. Text is entity-encoded
   (incl. `{` `}`); paths/keys/slugs are regex-validated; specs/values go through
   `jinja_string_literal()`. Variables compile to subscripts (`a["b"]`), never attributes.
2. **Sandbox:** `SafeEnvironment` (ImmutableSandboxedEnvironment) allows attribute access only on
   `LoopContext` and date/time. Don't widen `SAFE_ATTRIBUTE_TYPES` casually.
3. **Plain-data contexts:** `engine.ensure_plain()` rejects ORM objects. `TemplateType.build_context()`
   converts models to dicts. Never pass model instances into the engine.
4. **HTML contract** (`docs/html-contract.md`) is shared by `frontend/src/extensions.js` and
   `core/compiler.py`. Change both together, then run `cd frontend && npm run build && npm run contract`
   and `pytest tests/test_contract.py`.
5. **URL fetching** for PDF/DOCX goes through `fetchers.safe_url_fetcher` (data:, STATIC, MEDIA,
   allowlisted prefixes only). WeasyPrint ≥68 uses a `URLFetcher` class; `renderers/pdf.py:adapt_fetcher`
   bridges the classic dict-returning function API. Keep both working.
5b. **Typst source:** `TypstWriter` emits document text ONLY via `tstr()` string literals
   (`#"..."`). Anything emitted as code (colours, lengths, spans, widths) goes through the
   validators (`tcolor`, `tlength`, `_span`…). Compiles run in a temp root with only the
   generated file + images. Theme values are developer-provided Typst expressions.
5c. **Direction:** templates resolve "auto" with `formatting.direction_for(locale, direction)`;
   renderers get `RenderInput.direction` = "ltr"/"rtl". Each paragraph follows its first strong
   letter (`typst_pdf.first_strong`) in Typst, DOCX (`w:bidi` on/off, explicit `w:val="0"` in RTL
   docs) and HTML (`unicode-bidi: plaintext`). In bidi DOCX paragraphs jc "left"/"right" are
   logical, so the converter swaps them (verified in LibreOffice).
6. **Migrations:** released migrations are never edited, only added. Generate with
   `python -c` + `tests.settings` (see below) and check they import on Django 4.2.
7. Blocks are resolved **at render time** (single source of truth). Cache invalidation = version token
   in cache bumped by signals (`services.bump_version`). `generate()` snapshots compiled sources.
8. Formatting never raises; rendering errors are `TemplateRenderError`; never let a bad value crash a document.

## Commands

```bash
pip install -e ".[dev]"            # or -r requirements-dev.txt (no system libraries needed)
pytest                             # whole suite (~140 tests), <10s
pytest tests/test_compiler.py -q   # compiler/sanitiser
nox                                # py3.10–3.13 × Django 4.2/5.1/5.2
ruff check .

cd frontend && npm install
npm run build                      # → src/templates_pro/static/templates_pro/editor/ (commit it)
npm run watch
npm run contract                   # editor round-trip fixtures → tests/fixtures/editor_roundtrip/

cd example && python manage.py migrate && python manage.py seed_demo && python manage.py runserver
# admin / admin; pages: /, /editors/, /my-letter/, /admin/

# new migration for the package:
DJANGO_SETTINGS_MODULE=tests.settings python -c "import sys;sys.path[:0]=['.','src'];import django;django.setup();from django.core.management import call_command;call_command('makemigrations','templates_pro')"
```

## Conventions

- Public API = `templates_pro.services` (`render`, `render_to_response`, `generate`, `preview_document`,
  `get_constants`), `templates_pro.register/TemplateType/Var/Group/ListOf`, `widgets.TemplateEditorWidget`,
  `core.renderers.register_renderer`, settings keys. Changes there need a CHANGELOG entry and docs.
- User-visible strings in Django code use `gettext_lazy`. The editor UI is English (i18n is a roadmap item).
- Tests: add a test for every bug fix; security-relevant changes need a test in `test_compiler.py` /
  `test_engine.py`. Tests use `tests/testapp/doctemplate_types.py` (types `invoice`, `letter`).
- Docs live in `docs/*.md`; update the relevant page in the same change.
- Line length 100, ruff rules in `pyproject.toml`.

## Editor notes (frontend/src)

- `extensions.js`: custom nodes (tpVariable/tpConstant/tpDynamic inline atoms, tpBlock atom,
  tpRepeat/tpIf containers, TpTableRow with `repeat`/`as` attrs, `{{` trigger). Node views only
  re-render on attr changes (re-rendering on selection swallowed clicks).
- `editor.js`: `TemplateEditor` (toolbar presets, picker, format popover, dialogs, preview).
  Popovers are appended to `<body>` and wrapped in a `<div>`. Don't put popover classes on a `<form>`:
  inputs named `style` shadow `form.style` (DOM clobbering).
- Config comes from `widgets.editor_config()` via `json_script`; keep keys in sync.

## Roadmap / ideas (not done yet)

- Editor UI translations (UI is English; documents can be RTL).
- Per-paragraph direction override in the editor (today: first letter decides).
- DOCX: RTL bullet/numbering placement not verified in Word (LibreOffice shows bullets on the left).
- Template versions history / restore (only a version counter today).
- Image upload endpoint for the editor (today: URL or pasted data URI).
- Per-tenant constants (today: one global set + CONSTANTS_PROVIDER(request)).
- Optional inline conditions (today conditions are block-level sections).
