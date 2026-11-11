# Troubleshooting

Problems grouped by where you meet them. Installation problems on a fresh
machine (virtualenv, PowerShell, PyCharm) are in the
[setup guide](../SETUP.md#15-troubleshooting).

Start with:

```bash
python manage.py check                    # configuration problems
python manage.py templates_pro_validate   # templates and blocks that no longer validate
```

## Setting up

| Symptom | Cause | Fix |
|---|---|---|
| `no such table: templates_pro_documenttemplate` | migrations not applied | `python manage.py migrate` |
| `templates_pro.W002`: no template types are registered | no `doctemplate_types.py` found | create it in an app that is in `INSTALLED_APPS` ([quickstart.md](quickstart.md#1-declare-a-template-type)) |
| `Template type 'x' is not registered. Is the app that defines it installed?` | the app is not installed, or its `doctemplate_types.py` fails to import | check `INSTALLED_APPS`; run `python manage.py shell -c "import yourapp.doctemplate_types"` to see the import error |
| `ImproperlyConfigured: Template type 'x': Schema root 'const' is reserved` | a schema uses a reserved name | rename the root; `const`, `loop` and names starting with `tp_` are taken |
| `templates_pro.W001`: a format's library is not available | `PDF_ENGINE` is `"weasyprint"` without Pango | remove `PDF_ENGINE` to use Typst, or install Pango ([installation.md](installation.md#optional-weasyprint-as-the-pdf-engine)) |
| `templates_pro.E003` / `E004` | a theme's CSS file or `DEFAULT_THEME` is wrong | fix the static path in `THEMES`, or the theme key |
| `templates_pro_samples`: "Add templates_pro.samples to INSTALLED_APPS first" | the samples app is not installed | add it, then run the command again |

## The editor

| Symptom | Cause | Fix |
|---|---|---|
| A plain textarea instead of the editor | the editor's script and stylesheet are not loaded | put `{{ form.media }}` in the page's `<head>`; in production run `collectstatic` |
| The editor looks broken after an upgrade | an old bundle is being served | `collectstatic`, then reload without the browser cache |
| No **Preview** button | `templates_pro.urls` is not included | add `path("templates-pro/", include("templates_pro.urls"))` |
| Preview answers 403 | the user lacks `PREVIEW_PERMISSION` | grant `templates_pro.change_documenttemplate`, or change the setting |
| Preview is redirected to a login page | the preview pages require login | log the user in; set `LOGIN_URL` for your project |
| The picker shows no fields, or fields of the wrong type | the widget does not know the type | pass `template_type="…"`, or `type_field="…"` naming the form field that holds the type |
| A chip is red: "Unknown field … for this template type" | the field is not in the type's schema | pick another field, or add it to the schema |
| A block is missing from the block picker | it is inactive, or its *Template types* exclude this type | activate it, or tick the type on the block |
| "This template type has no lists to repeat" | the schema has no `ListOf` | add a `ListOf` to the schema and return a list in `build_context()` |
| The preview shows `[Field label]` or odd numbers | the schema has no `sample=` values | add samples, or override `sample_context()` ([template-types.md](template-types.md#sample_context)) |

## Saving

| Message | Cause | Fix |
|---|---|---|
| `unknown variable '…'` | the field was renamed or removed from the schema | remove the chip, or restore the field |
| `Block “…”: … (not provided by Invoice)` | a block used here needs a field this type lacks | use another block, or add the field to the type |
| `unknown block '…'` | the block was deleted or its slug changed | remove the block from the content, or recreate it with that slug |
| `Blocks include each other in a loop` | block A includes B, which includes A | remove one of the includes |
| `This block is used by other templates or blocks; its slug cannot change` | slugs are references | keep the slug; change the name instead |
| `'Row number' can only be used inside a repeat section or repeated row` | the chip is outside a repeat | move it into the repeat |
| `repeat item name '…' clashes with a variable group` | the alias equals a schema root | choose another name for the item |
| A constant chip is red ("Unknown constant"), yet the template saves | no active constant has that key | create it under **Admin → Constants**; until then the chip renders empty |

## Rendering

| Symptom | Cause | Fix |
|---|---|---|
| `TemplateNotAvailable: No document template matches 'x'` | no template has that slug, and no type `x` has a default template | check the slug, or tick **Default for its type** on one template |
| `TemplateNotAvailable: … is inactive` | the template is not active | activate it |
| `TemplateNotAvailable: … does not allow format 'docx'` | the format is not ticked on the template | tick it under *Output formats*, or pass `check_format=False` |
| `UnsafeContextError: context.invoice is a …Invoice` | `build_context()` returned a model instance or QuerySet | return dicts, lists and simple values only |
| `NotImplementedError: … build_context() must convert …` | the type has no `build_context()` and got an object | write one, or pass `data={...}` |
| `TemplateRenderError: missing block 'block:…'` | a block the template includes was deleted | recreate the block, or remove it from the template |
| `TemplateRenderError: a repeated list has more than 10000 items` | a list is too long | split the document, or paginate the data |
| A value is blank | the key is missing from the dict, or is `None` | return it from `build_context()`; set an "if empty, show" text on the chip |
| A repeat section prints nothing | the value is not a list, or is empty | return a `list` of dicts under the list's name |
| A condition never shows its content | the comparison is not numeric, or the value is empty | see the operator table in [concepts.md](concepts.md#conditions) |
| Wrong date or number style | the locale is not the one you expect | see the precedence in [formatting.md](formatting.md#what-it-is-formatted-with) |
| Wrong currency | the chip has its own currency, or `get_currency()` is missing | clear the chip's currency, or return one from `get_currency()` |
| A changed schema `format=` has no effect | defaults are compiled when a template is saved | `python manage.py templates_pro_validate --save` |
| An edited block or constant is not visible | it was changed with `QuerySet.update()` or raw SQL, which skips signals | `services.bump_version("blocks")` or `("constants")` |

## PDF and DOCX output

| Symptom | Cause | Fix |
|---|---|---|
| Images are missing | the URL is not allowed by the safe fetcher | use `/static/…` or `/media/…` paths or `data:` URIs, or add the host to `ALLOWED_URL_PREFIXES` |
| The header or footer overlaps the text | the margins are too small | raise the top/bottom margin, e.g. `25mm 18mm` |
| A project theme looks plain in PDF | the theme has no Typst style | add a `"typst"` entry ([rendering.md](rendering.md#themes)) |
| *Extra CSS* has no effect in PDF | Typst does not read CSS | style PDFs through the theme's Typst style, or use the WeasyPrint engine |
| DOCX ignores the theme | theme styling is not applied to DOCX | start from your own `.docx` ([rendering.md](rendering.md#styling-docx-output)) |
| Page numbers are empty | HTML and TXT have no pages | page numbers appear in PDF and DOCX only |
| A font is not used in PDF | Typst cannot find it | add its folder to `TYPST_FONT_PATHS` and name it in the theme's `font` |

## Right-to-left

| Symptom | Cause | Fix |
|---|---|---|
| A Hebrew document comes out left-to-right | direction is *Auto* and the locale is not Hebrew | set *Text direction* to *Right to left*, or *Locale* to `he_IL` |
| An English line in a Hebrew document is left-aligned | each paragraph follows its first letter (intended) | start the paragraph with Hebrew, or align it with the toolbar |
| The editor's toolbar stays left-to-right | the editor's interface is English only | nothing to fix; only the writing surface follows the direction |
