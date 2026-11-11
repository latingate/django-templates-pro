# The editor

The editor is a [TipTap](https://tiptap.dev) 3 bundle shipped prebuilt in
`templates_pro/static/templates_pro/editor/`. Projects need no Node toolchain.
It is exposed as a normal Django form widget.

## In the admin

The `DocumentTemplate` and `TemplateBlock` admins already use it. In the
template form the picker follows the **Template type** select. In the block
form it follows the **Template types** checkboxes (all types when none are
ticked).

## In your own forms

```python
from django import forms
from templates_pro.widgets import TemplateEditorWidget

class LetterForm(forms.Form):
    body = forms.CharField(widget=TemplateEditorWidget(
        template_type="customer_letter",    # fixed type...
        # type_field="template_type",       # ...or follow another field of this form
        preset="simple",
        skin="paper",
        height=480,
        placeholder="Write your letter…",
    ))
```

```django
<head>{{ form.media }}</head>
<form method="post">{% csrf_token %}{{ form }}</form>
```

Always validate submitted HTML on the server. `DocumentTemplate.full_clean()`
does this. For your own storage, use
`templates_pro.core.compiler.compile_html(body, schema=...)` and check
`.errors` (the demo's `LetterForm.clean_body` shows how).

### Widget options

| Option | Values | |
|---|---|---|
| `preset` | `full` (default), `simple`, `minimal` | toolbar richness |
| `skin` | `default`, `dark`, `paper`, `compact` | look |
| `template_type` | type key | fixed set of variables |
| `type_field` | form field name | variables follow that field's value |
| `types_field` | form field name | multi-select of types (blocks) |
| `toolbar` | list of item names | overrides the preset |
| `height` | px | minimum height |
| `preview` | `True` / `False` | Preview button (needs `templates_pro.urls`) |
| `placeholder` | text | empty-editor hint |
| `direction` | `"auto"` (default), `"ltr"`, `"rtl"` | text direction; *auto* follows the locale |
| `direction_field` | form field name | direction follows that field (the admin uses `direction`) |
| `locale_field` | form field name | locale used when direction is *auto* (the admin uses `locale`) |

Project-wide defaults go in `TEMPLATES_PRO["EDITOR"]`, e.g.
`{"preset": "simple", "skin": "paper", "height": 500}`.

### Toolbar items

`undo redo blockType fontSize bold italic underline strike color highlight
clear alignLeft alignCenter alignRight alignJustify bulletList orderedList
blockquote hr link image table variable constant dynamic block repeat
condition insert preview fullscreen`

Separators: `"|"` starts a new group, `"/"` starts a new row, and `">"`
right-aligns the rest.

```python
TemplateEditorWidget(toolbar=["bold", "italic", "|", "variable", "dynamic", ">", "preview"])
```

## Using it (end users)

- **Insert data**: click **Field**, **Constant**, **Date & time** or **Block**, or type
  `{{` anywhere. The picker has search, tabs (Tab / Shift+Tab), arrow keys,
  Enter and Esc.
- **Format a chip**: click it. The popover shows options for the chip's type
  with live examples, an "if empty, show" fallback and **Remove**.
- **Repeat**: select paragraphs → **Repeat**, or pick a *list* in the picker.
  For tables use **Table → Repeat this row for each item…**. Inside a
  repeat, the picker lists the current item's fields first.
- **Condition**: select content → **Condition**.
- **Blocks** appear as framed previews; **Change** swaps the block, **Remove**
  removes it. Edit block content under *Admin → Blocks*.
- **Preview** renders the unsaved content with sample data as HTML, PDF or TXT.
- Problems such as unknown fields or missing blocks are shown in red, and the
  status bar counts them.

## Right-to-left (Hebrew, Arabic…)

The writing surface follows the document's direction: set the template's
*Text direction* to *Right to left*, or leave it on *Auto* with a Hebrew or
Arabic *Locale*. The editor flips at once when either field changes, and the
status bar shows "Right to left". For your own forms:

```python
TemplateEditorWidget(template_type="customer_letter", direction="rtl")
# or follow fields of the same form:
TemplateEditorWidget(type_field="kind", direction_field="direction", locale_field="locale")
```

Each paragraph takes the direction of its first letter, exactly as in the
rendered documents; chips (field labels) don't count. The editor's own
toolbar, menus and popovers stay left-to-right and in English.

## Styling

Every colour is a CSS custom property, so you can restyle the editor without
rebuilding:

```css
.tp-skin-default { --tp-accent: #0f766e; --tp-var: #ccfbf1; --tp-var-fg: #115e59; }
.tp-editor { --tp-doc-font: "Inter", sans-serif; }
```

Main classes: `.tp-editor`, `.tp-toolbar`, `.tp-surface`, `.tp-chip--var|const|dynamic`,
`.tp-blocknode`, `.tp-section--repeat|if`, `.tp-pop` (popovers are appended
to `<body>`), `.tp-modal`.

## JavaScript API

The bundle defines `window.TemplatesPro` and auto-initialises every
`[data-tp-editor]` element, including ones added later (admin inlines, HTMX):

```js
const root = document.querySelector('[data-tp-editor]')
const ed = TemplatesPro.get(root)        // TemplateEditor instance
ed.editor                                 // the TipTap Editor
ed.editor.getHTML()
ed.openPicker({ tab: 'fields' })

// Initialise manually with your own config (see widgets.editor_config()):
TemplatesPro.init(element, config)
```

The textarea inside the root always holds the current HTML, so normal form
submission works.
