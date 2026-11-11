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

## Where the data comes from

A chip in the editor is only a placeholder: it shows the field's label, never
a value. Values arrive in one of two ways.

| When | Data | Built by |
|---|---|---|
| Editor **Preview**, admin preview links | sample data | `TemplateType.sample_context()`, from the schema's `sample=` values |
| `render()`, `render_to_response()`, `generate()` | real data | `TemplateType.build_context(obj, **kwargs)` |

A real render goes through these steps:

1. Your view loads an object and calls `render(template, obj, fmt=...)`.
2. The template's type converts it to a plain dict with `build_context()`.
3. The locale and currency are chosen
   ([template-types.md](template-types.md#locale-and-currency-hooks)).
4. Constants and the dynamic values are added to that dict, and the compiled
   template is rendered in the sandbox. A chip with path `customer.name`
   reads `customer["name"]` from the dict.
5. Included blocks and the page header/footer are rendered with **the same
   dict**.
6. The renderer for the format turns the resulting HTML into the output file.

The package never decides which model belongs to a template. That is your
view's job; see the demo's `document` view in
[the demo README](../example/README.md#how-the-demo-pages-get-their-data).

## Constants

Site-wide values edited in **Admin → Constants** (`company_name`, `vat_number`…),
shown as purple chips. Developers can add computed constants with
`CONSTANTS_PROVIDER` ([settings.md](settings.md)). Changing a constant changes
every document rendered afterwards.

- Constants don't depend on the schema, so they work in every template type
  and in every block.
- Admin constants and the provider's are merged. The provider wins when both
  define the same key.
- The provider is called as `provider(request=request)`. The request is
  whatever the caller passed to `render(..., request=request)`, so it can be
  `None` (background tasks, the editor's field list).
- A chip whose key is not defined is a **warning**, not an error: the template
  saves and the chip renders empty. The same happens when a constant is later
  deleted or deactivated.
- There is one global set of constants. For per-tenant values, return
  different values from the provider based on the request.

## Dynamic values

Green chips that are filled in at render time. The list is fixed by the
package. For a computed value of your own, use `CONSTANTS_PROVIDER` or add it
to `build_context()`.

| Key | Value | Notes |
|---|---|---|
| `now` | current date & time | site time zone |
| `today` | current date | |
| `time` | current time | |
| `year` | current year | |
| `row_number` | 1, 2, 3… | only inside a repeat section / repeated row |
| `page_number`, `page_count` | page X of Y | PDF and DOCX only (empty in HTML/TXT) |

`now`, `today`, `time` and `year` all come from one instant, the moment of
rendering, so they agree within a document. Pass `render(..., now=...)` to
fix that instant (tests, back-dating). They are formatted in the document's
locale like any other chip.

Page numbers are not known while the template is rendered. The compiler
leaves a placeholder and the PDF or DOCX renderer fills it in, which is why
they belong in page header and footer blocks.

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

A block has no data of its own. It is rendered with the same data as the
template that includes it, so a `customer-details` block shows the invoice's
customer in an invoice and the order's customer in an order confirmation. It
can only use fields that the including template's type provides.

A template uses a block in one of two ways: inserted in the content with the
**Block** button, or chosen as the template's *Page header* / *Page footer*.

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

Repeats can be nested (an item's own list), up to 20 levels.

- The alias names the current item. Inside the repeat, fields are written
  `line.description`. An alias cannot equal a schema root name such as
  `invoice`.
- The `row_number` dynamic value gives the position, starting at 1.
- An empty or missing list outputs nothing.
- A list with more than 10,000 items stops the render with an error.

## Conditions

Select content and click **Condition** to show it only if a field *has a
value*, *is empty*, *equals*, *is greater than*… a value. Typical uses are a
"Discount" line only when there is a discount, or a "Paid" stamp.

A condition tests one field with one operator against a fixed value:

| Operator | Shows the content when |
|---|---|
| `truthy` / `falsy` | the value is non-empty and true / is empty or false |
| `eq` / `ne` | equal / not equal. Compared as numbers when both sides are numbers, otherwise as text |
| `gt`, `gte`, `lt`, `lte` | numeric comparison. False when either side is not a number |
| `contains` | the text contains the value, or the list has it as an item |

What conditions don't do:

- **No "and" / "or".** Put one condition inside another for "and".
- **No "else".** Add a second condition with the opposite operator.
- **No comparing two fields.** Compute a boolean in `build_context()` and test
  that (the demo's `employee.is_current`).
- **No inline conditions.** A condition wraps whole paragraphs or blocks.

A test that cannot be evaluated counts as false: the content is hidden and
the document still renders. Conditions and repeats nest freely, so a
condition inside a repeat can test the current item (`line.amount`).

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
