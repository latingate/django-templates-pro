# The admin

Installing the package adds four sections to the Django admin, under
**Document templates**. This page describes each one and the preview pages they
link to.

## Document templates

One row per template. The list shows the type, theme, enabled formats,
whether it is the default for its type, its version and **preview links**
(one per format; they need `templates_pro.urls`, see
[installation.md](installation.md#configure-django)).

The form has five groups of fields:

| Group | Fields | Notes |
|---|---|---|
| (top) | *Name*, *Slug*, *Template type*, *Description*, *Active*, *Default for its type* | The slug is what code passes to `render("my-slug", ...)`. Only one template per type can be the default. |
| Content | the editor | The field picker follows the *Template type* select. See [editor.md](editor.md). |
| Output | *Output formats*, *Theme*, *Locale*, *Text direction*, *File name* | Formats come from `OUTPUT_FORMATS`. *File name* is a pattern such as `invoice-{invoice.number}`; empty uses the type's default. |
| Page | *Page size*, *Orientation*, *Margins*, *Page header*, *Page footer*, *Extra CSS* | Header and footer are blocks repeated on every PDF/DOCX page. *Extra CSS* applies to HTML output (and WeasyPrint PDFs). |
| Info | *Version*, *Updated*, *Variables used*, *Blocks used* | Read-only. *Blocks used* includes nested blocks and the header/footer. |

What happens on **Save**:

1. The content is sanitised and compiled. Unknown fields, unknown blocks and
   invalid formats are reported as errors on the content field, and nothing
   is saved.
2. Blocks the template uses are checked against the template's type, so a
   block that needs `customer.name` cannot be used in a type without it.
3. The **version** goes up by one when the compiled content changed. It is a
   counter only: there is no history to restore from.

Other things to know:

- **Inactive** templates cannot be rendered by slug or type key: `render()`
  raises `TemplateNotAvailable`.
- **Default for its type** is what `render("invoice", obj)` (a type key
  instead of a slug) uses.
- The action **Duplicate selected templates** copies a template as
  `<slug>-copy`, not default, version 1. Use it to try changes safely.
- A template whose type is no longer registered is shown as
  `key (unregistered)` and keeps its type until you change it.

## Blocks

Reusable content ([concepts.md](concepts.md#shared-blocks)).

| Field | Notes |
|---|---|
| *Name*, *Slug* | Templates reference the slug. It cannot change while the block is in use. |
| *Category* | Header, Footer, Content, Signature or Other. Shown next to the block's name in the editor's picker and used as a filter in this list. |
| *Active* | An inactive block renders as empty wherever it is used. |
| *Template types* | Types whose fields the block may use. None ticked: usable everywhere, and the editor offers the fields of all types. |
| *Content* | The same editor. Blocks can contain other blocks. |
| *Used by* | Read-only list of the templates and blocks that include this one, with links. |

Saving a block changes every document rendered afterwards; nothing needs to
be re-saved. A block that is a template's page header or footer cannot be
deleted until the template stops using it. Deleting a block that templates
include in their content is allowed, and those templates then fail to render
with "missing block": check *Used by* first, or deactivate the block instead.

## Constants

Site-wide values ([concepts.md](concepts.md#constants)). *Value* and *Active*
can be edited straight in the list. *Key* is what templates store, so
renaming a key empties the chips that use it; *Label* is only what the editor
shows. Constants from `CONSTANTS_PROVIDER` are not listed here: they exist in
code only.

## Generated documents

A read-only log of what `services.generate()` produced
([rendering.md](rendering.md#storing-generated-documents)): file, format,
size, SHA-256 checksum, the template and its version at the time, the object
it was made for, the user and a snapshot of the compiled template and blocks.
Rows cannot be added or edited in the admin. Deleting a template keeps its
generated documents.

Plain `render()` and `render_to_response()` calls are **not** logged here.

## Preview pages

| URL | Used by | Data |
|---|---|---|
| `POST templates-pro/preview/` | the editor's **Preview** button (unsaved content) | sample data |
| `GET templates-pro/preview/<pk>/<fmt>/` | the preview links in the template list | sample data |

Both show the document with the type's **sample data**
([template-types.md](template-types.md#sample_context)), never with real
records. HTML, PDF and TXT open in the browser; DOCX downloads. When the
template cannot be rendered, the page lists the reasons instead.

The saved-template preview ignores the template's *Output formats*, so you
can check a format before enabling it.

## Permissions

The admin uses Django's model permissions.

| To let someone… | Grant |
|---|---|
| write and edit templates | `templates_pro.add_documenttemplate`, `change_documenttemplate` |
| edit shared blocks | `templates_pro.change_templateblock` |
| edit constants | `templates_pro.change_siteconstant` |
| see issued documents | `templates_pro.view_generateddocument` |
| use the previews | `PREVIEW_PERMISSION` (default `templates_pro.change_documenttemplate`) |

Anyone who can edit templates of a type can print every value its
`build_context()` returns. See [security.md](security.md#3-plain-data-contexts).
