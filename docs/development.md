# Development

## Layout

```
src/templates_pro/
  core/              # pure Python; no Django imports
    schema.py        #   Var / Group / ListOf, sample data, schema JSON for the editor
    compiler.py      #   editor HTML -> Jinja (+ sanitiser), the HTML contract
    engine.py        #   sandboxed environment, plain-data check, limits
    formatting.py    #   Babel formatting + condition tests
    renderers/       #   html, typst_pdf (default PDF), pdf (WeasyPrint, optional),
                     #   docx (python-docx), txt (html2text)
  registry.py        # TemplateType + register()
  models.py          # SiteConstant, TemplateBlock, DocumentTemplate, GeneratedDocument
  services.py        # public API: render / render_to_response / generate / preview
  engines.py         # registers the PDF renderer chosen by PDF_ENGINE
  widgets.py forms.py admin.py views.py urls.py checks.py fetchers.py themes.py conf.py
  samples/           # optional app: sample types + starter content (templates_pro_samples)
  fonts/             # bundled Noto Sans + Noto Sans Hebrew (SIL OFL 1.1) for Typst
  static/templates_pro/editor/   # BUILT editor bundle (committed)
  static/templates_pro/themes/   # document themes
frontend/            # editor source (TipTap 3, Vite)
example/             # demo project + sample templates/blocks (demo/samples/)
tests/               # pytest-django
docs/
```

## Python

```bash
pip install -e ".[dev]"        # or: pip install -r requirements-dev.txt
pytest                       # about 140 tests, under 10 s
nox                          # Python 3.10–3.13 × Django 4.2 / 5.1 / 5.2
ruff check .
```

## Editor bundle

```bash
cd frontend
npm install
npm run build        # writes src/templates_pro/static/templates_pro/editor/
npm run watch        # rebuild on change (unminified, with source maps)
npm run contract     # re-generate tests/fixtures/editor_roundtrip/
```

Commit the built bundle. It ships inside the wheel, so projects never need
Node. After changing node markup in `extensions.js` or the compiler, run
`npm run contract` and `pytest tests/test_contract.py`: these check that
what the real editor emits compiles identically.

## Checking PDF and DOCX output by eye

Tests check structure (e.g. RTL markers in DOCX XML); looking is still worth
it after changing a renderer or theme. Render the demo documents
(`/doc/<slug>/<pk>.pdf`), rasterise them with `pdftoppm -png`, and convert
DOCX with `soffice --headless --convert-to pdf` (LibreOffice) to see Word
output.

To try a Typst change quickly, print the generated source:

```python
from pathlib import Path
from templates_pro.core.renderers import RenderInput
from templates_pro.core.renderers.typst_pdf import TypstPdfRenderer
print(TypstPdfRenderer().build_source(RenderInput(body_html="<p>שלום</p>", direction="rtl", lang="he"), Path("/tmp")))
```

Try changes in the demo:

```bash
cd example && python manage.py runserver
```

## Releasing

1. Update `__version__` in `src/templates_pro/__init__.py` and `CHANGELOG.md`.
2. `cd frontend && npm run build`, then commit.
3. `pytest && nox`
4. `python -m build` and inspect the wheel (it should contain `static/templates_pro/editor/*`).
5. Tag `vX.Y.Z`; publish to your index (`twine upload`, or install from the git tag).
