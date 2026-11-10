# Development

## Layout

```
src/templates_pro/
  core/              # pure Python; no Django imports
    schema.py        #   Var / Group / ListOf, sample data, schema JSON for the editor
    compiler.py      #   editor HTML -> Jinja (+ sanitiser), the HTML contract
    engine.py        #   sandboxed environment, plain-data check, limits
    formatting.py    #   Babel formatting + condition tests
    renderers/       #   html, pdf (WeasyPrint), docx (python-docx), txt (html2text)
  registry.py        # TemplateType + register()
  models.py          # SiteConstant, TemplateBlock, DocumentTemplate, GeneratedDocument
  services.py        # public API: render / render_to_response / generate / preview
  widgets.py forms.py admin.py views.py urls.py checks.py fetchers.py themes.py conf.py
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
pytest                       # 100+ tests, about 3 s
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
