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
`UnsafeContextError` (non-plain context) and `RendererUnavailable` (missing
WeasyPrint or python-docx).

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
| `html` | built in | full document with theme CSS; header/footer blocks shown in-flow |
| `pdf` | WeasyPrint | CSS paged media; header/footer repeat on every page; page numbers |
| `docx` | python-docx | headings, inline styles, lists, tables (colspan), images, links, page setup, header/footer with PAGE/NUMPAGES fields. **Theme CSS is not applied.** |
| `txt` | html2text | readable text with light Markdown (headings, bullets, pipe tables) |

Enable formats per project with `TEMPLATES_PRO["OUTPUT_FORMATS"]`. Each
template then ticks the formats it allows.

## Themes

Themes are CSS for HTML and PDF output. The built-ins are `classic` (serif),
`modern` (sans-serif with an accent colour; set `--tp-accent` in the
template's extra CSS), `minimal`, `corporate` (banded tables) and `none`.

Add your own:

```python
TEMPLATES_PRO = {"THEMES": {
    "brand": {"label": "Our brand", "css": "myapp/doc-themes/brand.css"},   # a static path
}}
```

Useful selectors are `.tp-body` (page), `.tp-document` (content),
`.tp-running-header` and `.tp-running-footer`. In PDF, `@page` is generated
from the template's page size, orientation and margins. You can add your own
`@page` rules in the theme or in the template's extra CSS.

Fonts: WeasyPrint uses fonts installed on the server. For web fonts, load
them with `@font-face` from your static files (allowed by the URL fetcher).

## Page header and footer

Set *Page header* / *Page footer* on a template to any block. In PDF they are
CSS running elements. In DOCX they become the section header and footer. Use
the `page_number` and `page_count` dynamic values inside them. Leave enough
top/bottom margin, for example `25mm 18mm`.

## Images

Images may be `data:` URIs or URLs under `STATIC_URL` / `MEDIA_URL`. Remote
URLs are blocked unless they match `TEMPLATES_PRO["ALLOWED_URL_PREFIXES"]`
(see [security.md](security.md#url-fetching)).

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
`css`, `page` (size, orientation, margin), `lang`, `base_url` and
`url_fetcher`.

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
`extra_css`, `locale`, `fmt`) renders unsaved content with sample data.
`GET templates-pro/preview/<pk>/<fmt>/` renders a saved template. Both
require `PREVIEW_PERMISSION`.
