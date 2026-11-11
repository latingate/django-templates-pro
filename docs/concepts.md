# Concepts

```
Template type (code)          DocumentTemplate (admin)          Output
 schema + build_context  ──▶   editor HTML ─compile─▶ Jinja ──▶  HTML · PDF (Typst) · DOCX · TXT
                                 │ includes
                                 ▼
                         TemplateBlock (admin)   SiteConstant (admin)
```

## Template types

Developers define these in code ([template-types.md](template-types.md)). A
type declares a **schema** of variables and converts your objects to plain
data. Each `DocumentTemplate` belongs to exactly one type, and the editor only
offers that type's variables.

## Variables

Values from the schema, such as `invoice.number` or `customer.name`. In the
editor they are blue **chips**. Unknown variables are flagged in the editor
(red chip) and rejected on save. That includes variables used inside blocks.

## Constants

Site-wide values edited in **Admin → Constants** (`company_name`, `vat_number`…),
shown as purple chips. Developers can add computed constants with
`CONSTANTS_PROVIDER` ([settings.md](settings.md)). Changing a constant changes
every document rendered afterwards.

## Dynamic values

Green chips that are filled in at render time:

| Key | Value | Notes |
|---|---|---|
| `now` | current date & time | site time zone |
| `today` | current date | |
| `time` | current time | |
| `year` | current year | |
| `row_number` | 1, 2, 3… | only inside a repeat section / repeated row |
| `page_number`, `page_count` | page X of Y | PDF and DOCX only (empty in HTML/TXT) |

## Formatting

Every chip can carry a format: date style or pattern, decimals, currency,
symbol or ISO code, letter case, yes/no labels, and a fallback text for empty
values. The schema supplies defaults (a `money` variable is formatted as money
unless the user changes it). Formatting is locale-aware through Babel. See
[formatting.md](formatting.md).

## Shared blocks

A **block** is reusable content edited in **Admin → Blocks**: letterheads,
footers, customer address panels, payment terms, signatures. Templates include
blocks by slug. Blocks are resolved when a document renders, so **editing a
block updates every template that uses it**. There is one source of truth.

- Blocks can include other blocks. The package detects and refuses include cycles.
- A block's **template types** restrict which variables it may use. With no
  types, it is "shared by all": it can still use variables, but every
  template that includes it is validated against its own type.
- **Page header / footer**: a template can name a block to repeat at the top
  or bottom of every PDF/DOCX page (use `page_number`/`page_count` there).
- A block's slug cannot change while it is in use. Inactive blocks render
  as empty.
- The block admin page lists where each block is used.

## Repeat sections and repeated rows

For list variables (`ListOf`):

- **Repeat section**: select paragraphs and click **Repeat**. The content
  repeats once per item, and item fields appear in the picker under the alias
  you chose (`line › Description`).
- **Repeated table row**: in a table row, **Table → Repeat this row for each
  item…**. This is the usual way to build invoice line tables.

Repeats can be nested (an item's own list).

## Conditions

Select content and click **Condition** to show it only if a field *has a
value*, *is empty*, *equals*, *is greater than*… a value. Typical uses are a
"Discount" line only when there is a discount, or a "Paid" stamp.

## Text direction (RTL)

Every template has a **Text direction**: *Auto* (the default), *Left to
right* or *Right to left*. *Auto* is right-to-left when the render locale's
language is Hebrew, Arabic, Persian, Urdu, Yiddish (and a few more), and
left-to-right otherwise. The render locale is the template's own *Locale*,
or the object's (`TemplateType.get_locale`), or the site default.

Direction applies everywhere:

- **Editor**: the writing surface flips as soon as you change the
  *Direction* or *Locale* field.
- **HTML**: `<html dir="rtl" lang="he">`.
- **PDF**: Typst lays out right to left, including table columns, lists and
  page headers/footers.
- **DOCX**: right-to-left paragraphs, tables and section, with Hebrew/Arabic
  runs marked as complex script.
- **TXT**: plain Unicode, which readers display correctly.

**Each paragraph takes the direction of its first letter.** For example, an
English address line inside a Hebrew document stays left-to-right, and a
Hebrew sentence in an English document stays right-to-left. That is the same
rule as CSS `unicode-bidi: plaintext`, and HTML, PDF and DOCX follow it
alike. In the editor, chips don't count, because they show field labels and
not the values.

Explicit alignment from the toolbar (left, centre, right) is kept as you see
it in the editor, in every format.

## Themes and page setup

A template picks a **theme**, page size, orientation, margins and optional
extra CSS. A theme is CSS for HTML output (and for PDF when the WeasyPrint
engine is used), plus a matching Typst style for the default PDF engine.
Built-in themes are `classic`, `modern`, `minimal`, `corporate` and `none`.
Projects can add their own ([rendering.md](rendering.md#themes)). *Extra CSS*
affects HTML output only (and WeasyPrint PDFs).

## Generated documents

`services.generate()` stores the rendered file together with the template
version, a snapshot of the compiled template and blocks, a checksum and a link
to the source object. Use it for anything legal (invoices, contracts), so that
later block edits never change what was issued.
