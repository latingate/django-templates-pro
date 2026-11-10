# Settings reference

All settings live in one dict:

```python
TEMPLATES_PRO = {
    "DEFAULT_CURRENCY": "EUR",
}
```

| Key | Default | Description |
|---|---|---|
| `DEFAULT_LOCALE` | `None` → `LANGUAGE_CODE` | Babel locale for formatting (`en_GB`, `de-de` both accepted) |
| `TIME_ZONE` | `None` → `TIME_ZONE` when `USE_TZ` | zone for dynamic values and aware datetimes |
| `DEFAULT_CURRENCY` | `"USD"` | money currency when neither chip nor `get_currency()` sets one |
| `OUTPUT_FORMATS` | `["html", "pdf", "docx", "txt"]` | formats enabled in this project |
| `DEFAULT_OUTPUT_FORMATS` | `["html", "pdf"]` | pre-ticked for new templates |
| `DEFAULT_THEME` | `"classic"` | theme for new templates |
| `THEMES` | `{}` | extra themes: `{"key": {"label": "...", "css": "static/path.css"}}` |
| `DEFAULT_PAGE_SIZE` | `"A4"` | `A3`, `A4`, `A5`, `Letter`, `Legal` |
| `DEFAULT_MARGIN` | `"20mm"` | CSS margin shorthand |
| `CONSTANTS_PROVIDER` | `None` | dotted path to `callable(request=None) -> dict`, merged over admin constants |
| `RENDER_TIMEOUT` | `15` | seconds of template execution (not PDF layout) |
| `MAX_OUTPUT_CHARS` | `5_000_000` | rendered HTML size limit |
| `URL_FETCHER` | `None` | dotted path replacing the safe fetcher |
| `ALLOWED_URL_PREFIXES` | `[]` | remote URL prefixes allowed for images/CSS in PDF/DOCX |
| `PREVIEW_PERMISSION` | `"templates_pro.change_documenttemplate"` | required for preview endpoints (`None` = any logged-in user) |
| `EDITOR` | `{"preset": "full", "skin": "default", "height": 460}` | widget defaults |
| `STORAGE` | `None` | `STORAGES` alias for generated files (`None` = default storage) |
| `UPLOAD_TO` | `"templates_pro/generated/%Y/%m/"` | strftime path for generated files |
| `CACHE_ALIAS` | `"default"` | cache used for block/constant version tokens |

## System checks

| ID | Meaning |
|---|---|
| `templates_pro.E001` | a format in `OUTPUT_FORMATS` has no renderer |
| `templates_pro.E002` | `DEFAULT_OUTPUT_FORMATS` lists a disabled format |
| `templates_pro.E003` | a theme's CSS file cannot be found |
| `templates_pro.E004` | `DEFAULT_THEME` is unknown |
| `templates_pro.W001` | an enabled format's library (WeasyPrint/python-docx) is missing |
| `templates_pro.W002` | no template types are registered |
