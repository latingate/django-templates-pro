# Rendering

## The services API

```python
from templates_pro.services import render, render_to_response, generate
```

### `render(template, obj=None, *, fmt=None, data=None, locale=None, sample=False, request=None, now=None, check_format=True, **kwargs)`

Returns a `RenderedDocument` with `content` (bytes), `fmt`, `mimetype`,
`filename`, `template`, `.text` (decoded) and `.as_response(attachment=True)`.

`template` can be:

- a `DocumentTemplate` instance
- its slug, e.g. `"invoice-standard"`
- its primary key
- a **type key**, e.g. `"invoice"`, which uses that type's default template (*Default for its type*)

| Argument | |
|---|---|
| `obj` | passed to `TemplateType.build_context(obj, **kwargs)` |
| `data` | a ready plain-data context (skips `build_context`) |
| `fmt` | `html`, `pdf`, `docx`, `txt` (default: the template's first format) |
| `locale` | force a locale (see [template-types.md](template-types.md#locale-and-currency-hooks)) |
| `sample` | render with the type's sample data |
| `request` | passed to `CONSTANTS_PROVIDER` |
| `now` | fixed "current time" (tests, back-dating) |
| `check_format` | refuse formats the template doesn't enable (default `True`) |

It raises `TemplateNotAvailable` (unknown or inactive template, or a disabled
format), `TemplateRenderError` (a missing block or a limit exceeded),
`UnsafeContextError` (non-plain context) and `RendererUnavailable` (only when
the optional WeasyPrint engine is selected but not installed).

### `render_to_response(template, obj=None, *, fmt=None, attachment=True, **kwargs)`

The same as `render(...).as_response()`. The file name comes from the
template's *File name* field or the type's `filename`, with tokens filled in
and made filesystem-safe.

### Examples

```python
# Download
return render_to_response("invoice", invoice, fmt="pdf")

# Inline in the browser
return render_to_response("invoice", invoice, fmt="pdf", attachment=False)

# Email: HTML body plus plain-text alternative plus PDF attachment
from django.core.mail import EmailMultiAlternatives
html = render("order-confirmation", order, fmt="html").text
text = render("order-confirmation", order, fmt="txt").text
pdf = render("invoice", order.invoice, fmt="pdf")
msg = EmailMultiAlternatives("Your order", text, to=[order.customer.email])
msg.attach_alternative(html, "text/html")
msg.attach(pdf.filename, pdf.content, pdf.mimetype)
msg.send()

# Celery task: return bytes, or store them (see generate())
@shared_task
def build_statement(customer_id):
    customer = Customer.objects.get(pk=customer_id)
    return generate("statement", customer, fmt="pdf").pk
```

## Storing generated documents

```python
record = generate("invoice", invoice, fmt="pdf", user=request.user)
record.file.url, record.checksum, record.template_version, record.snapshot
```

`generate()` renders and saves a `GeneratedDocument` containing the file (in
`TEMPLATES_PRO["STORAGE"]`, under `UPLOAD_TO`), the SHA-256 checksum, the
template and its version, the compiled template **and every block it used**
(`snapshot`), the source object (generic FK) and the user. The admin shows
these records read-only.

Use it whenever a document must not change after issue. Live rendering always
uses the current blocks and constants.

## Formats

| Format | Engine | Notes |
|---|---|---|
| `html` | built in | full document with theme CSS and `dir`/`lang`; header/footer blocks shown in-flow |
| `pdf` | **Typst** (default) | pure pip; right-to-left incl. tables; header/footer repeat on every page; page X of Y; bundled Latin + Hebrew fonts |
| `docx` | python-docx | headings, inline styles, lists, tables (colspan), images, links, page setup, header/footer with PAGE/NUMPAGES fields, right-to-left. **Theme styling is not applied.** |
| `txt` | html2text | readable text with light Markdown (headings, bullets, pipe tables) |

Enable formats per project with `TEMPLATES_PRO["OUTPUT_FORMATS"]`. Each
template then ticks the formats it allows.

## PDF engines

| | `"typst"` (default) | `"weasyprint"` (optional) |
|---|---|---|
| Install | included, pip only | `pip install "django-templates-pro[weasyprint]"` + Pango system library |
| Hebrew / RTL, tables included | ✔ | ✔ |
| Styling | the theme's Typst style | the theme's CSS, plus the template's extra CSS |
| Speed | fast | slower |

```python
TEMPLATES_PRO = {"PDF_ENGINE": "weasyprint"}   # default: "typst"
```

**How Typst output is made:** Typst doesn't read HTML, so the package
converts the editor's HTML (a small, known subset) into Typst markup. It
supports headings, paragraphs and alignment, bold, italic, underline,
strike-through, sub/superscript, highlight, text colour and size, links,
lists (nested, numbered with a start), quotes, code, horizontal lines, tables
(header rows repeat on each page; merged cells; cell fill), images, and
header/footer blocks with page numbers. The template's *Extra CSS* does not
apply to Typst PDFs.

**Fonts:** the package bundles Noto Sans and Noto Sans Hebrew, and Typst
bundles Libertinus Serif (which also has Hebrew), so output looks the same on
every machine. Installed system fonts are used too, unless
`TYPST_IGNORE_SYSTEM_FONTS` is `True`. Add your own font folders with
`TYPST_FONT_PATHS` and name the fonts in a theme's `font` value.

## Themes

A theme has two parts:

- **CSS** for HTML output (and for PDF with the WeasyPrint engine). Useful
  selectors: `.tp-body` (page), `.tp-document` (content),
  `.tp-running-header` and `.tp-running-footer`, and `[dir=rtl]` for
  right-to-left rules.
- **A Typst style** for PDF output with the default engine: a set of values
  (fonts, sizes, colours, table look).

The built-ins are `classic` (serif), `modern` (sans-serif with an accent
colour), `minimal`, `corporate` (banded tables) and `none`. Each has both
parts.

Add your own:

```python
TEMPLATES_PRO = {"THEMES": {
    "brand": {
        "label": "Our brand",
        "css": "myapp/doc-themes/brand.css",          # a static path (HTML output)
        "typst": {                                     # PDF output (optional)
            "base": "modern",                          # start from a built-in style
            "accent": 'rgb("#0f766e")',
            "h1-color": 'rgb("#0f766e")',
            "th-fill": 'rgb("#0f766e")',
            "font": '("Inter", "Noto Sans Hebrew")',   # fonts from TYPST_FONT_PATHS or the system
        },
    },
}}
```

The Typst values are Typst expressions written as Python strings. Without a
`"typst"` entry, PDFs use the `minimal` style. Available keys:

| Key | What it styles | Example |
|---|---|---|
| `font`, `heading-font` | body / heading font list | `'("Noto Sans", "Noto Sans Hebrew")'` |
| `size`, `leading` | body size, line spacing | `"10.5pt"`, `"0.65em"` |
| `fg`, `muted`, `accent`, `link` | text, header/footer, accent, link colours | `'rgb("#222222")'` |
| `heading-color`, `h1-color` | heading colours | `'rgb("#1e3a5f")'` |
| `h1-size`, `h2-size`, `h3-size` | heading sizes | `"20pt"` |
| `h1-weight` | `'"regular"'`, `'"semibold"'`, `'"bold"'` | |
| `h1-rule`, `h2-rule` | a line under the heading, or `"none"` | `'2pt + rgb("#1e3a5f")'` |
| `h3-style`, `h3-upper` | `'"italic"'`; `"true"` for upper case | |
| `th-fill`, `th-fg`, `th-line` | table header fill, text colour, line under it | `'rgb("#2563eb")'`, `"none"` |
| `row-line`, `band`, `table-frame` | line under each row, every-other-row fill, outer border | `'0.6pt + rgb("#e2e8f0")'` |
| `quote-line`, `quote-fill`, `quote-style` | quote bar, background, `'"italic"'` | |
| `rule` | horizontal line colour | `'rgb("#dddddd")'` |

Fonts: WeasyPrint uses fonts installed on the server. For web fonts, load
them with `@font-face` from your static files (allowed by the URL fetcher).
Typst uses the bundled fonts, `TYPST_FONT_PATHS` and system fonts.

## Page header and footer

Set *Page header* / *Page footer* on a template to any block. In PDF they
repeat on every page (Typst page header/footer, or CSS running elements with
WeasyPrint). In DOCX they become the section header and footer. Use
the `page_number` and `page_count` dynamic values inside them. Leave enough
top/bottom margin, for example `25mm 18mm`.

## Images

Images may be `data:` URIs or URLs under `STATIC_URL` / `MEDIA_URL`. Remote
URLs are blocked unless they match `TEMPLATES_PRO["ALLOWED_URL_PREFIXES"]`
(see [security.md](security.md#url-fetching)). PNG, JPEG, GIF, WebP and SVG
work in Typst PDFs. DOCX takes PNG, JPEG and GIF.

## Custom renderers

```python
from templates_pro.core.renderers import Renderer, RenderInput, register_renderer

class MarkdownRenderer(Renderer):
    name, mimetype, extension, label = "md", "text/markdown", "md", "Markdown"

    def render(self, doc: RenderInput) -> bytes:
        import html2text
        return html2text.html2text(doc.body_html).encode()

register_renderer(MarkdownRenderer())      # e.g. in AppConfig.ready()
# then add "md" to TEMPLATES_PRO["OUTPUT_FORMATS"]
```

`RenderInput` carries `body_html`, `header_html`, `footer_html`, `title`,
`css`, `theme` (key), `page` (size, orientation, margin), `lang`,
`direction` (`"ltr"`/`"rtl"`, already resolved), `base_url` and
`url_fetcher`.

The built-in PDF renderer is `templates_pro.core.renderers.typst_pdf.TypstPdfRenderer`.
`TEMPLATES_PRO["PDF_ENGINE"]` registers it, or WeasyPrint, under `"pdf"` at
startup. Registering your own renderer named `"pdf"` in `AppConfig.ready()`
of an app listed *after* `templates_pro` replaces both.

### Styling DOCX output

Subclass the built-in renderer and start from your own `.docx` with your
corporate styles (Heading 1–6, List Bullet, List Number, Quote, Table Grid):

```python
import docx
from templates_pro.core.renderers import register_renderer
from templates_pro.core.renderers.docx import DocxRenderer

class BrandDocx(DocxRenderer):
    def new_document(self, doc):
        d = docx.Document("myapp/word/brand.docx")
        for p in list(d.paragraphs):          # drop the sample body content
            p._element.getparent().remove(p._element)
        return d

register_renderer(BrandDocx())   # replaces "docx"
```

## Previews

`POST templates-pro/preview/` (JSON or form data: `body`, `template_type`,
`theme`, `header_block`, `footer_block`, `page_size`, `orientation`, `margin`,
`extra_css`, `locale`, `direction`, `fmt`) renders unsaved content with sample data.
`GET templates-pro/preview/<pk>/<fmt>/` renders a saved template. Both
require `PREVIEW_PERMISSION`.
