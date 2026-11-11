# Formatting reference

Users set formats in the editor by clicking a chip. Underneath, each chip
stores a small JSON *format spec* (`data-format`). Every option below can also
be set as a schema default with `Var(..., format={...})`.

All formatting is done by [Babel](https://babel.pocoo.org/) in the render
locale. Rounding is commercial (half up). Bad values never break a document:
they are printed as-is and a warning is logged to the `templates_pro` logger.

## How formatting works

Formatting is a property of the **chip**, not of the data. Your
`build_context()` returns raw values (a `Decimal`, a `date`, a `bool`); each
chip decides how its value is written. The same `invoice.date` can appear as
`15/01/2026` in a table and as `Thursday, 15 January 2026` in a sentence.

### Setting a format in the editor

Click a chip. The popover offers the options that fit the field's type:

| Field type | Options offered |
|---|---|
| `date`, `datetime`, `time` | style (short, medium, long, full, each with a live example) or a custom pattern |
| `money` | currency, decimal places, symbol or ISO code |
| `number`, `integer`, `percent` | decimal places |
| `boolean` | text when yes, text when no |
| `string`, `text`, `email`, `url`, constants | letter case |

Every type also has **If empty, show** (the fallback). Page number chips have
no options. Variables, constants and dynamic values are all formatted the
same way.

### Which format applies

For one chip, the first of these that exists is used:

1. the format chosen on the chip
2. the schema default of the variable: `Var(..., format={...})`
3. the default for the variable's type (see
   [template-types.md](template-types.md#schema-nodes))

A chip's own format replaces the schema default as a whole; the two are not
mixed at render time. The editor's popover starts from the schema default, so
what you see there is what gets saved.

Steps 2 and 3 are resolved **when the template is saved**, and the result is
stored in the compiled template. After changing a `format=` in a schema, run
`python manage.py templates_pro_validate --save` to re-compile existing
templates.

### What it is formatted with

Three things come from the render, not from the chip:

| | Order of precedence |
|---|---|
| **Locale** (month names, separators, digit grouping) | `render(locale=...)`, the template's *Locale* field, `TemplateType.get_locale(obj)`, `DEFAULT_LOCALE`, `LANGUAGE_CODE` |
| **Currency** (for `money` without its own currency) | the chip's currency, `TemplateType.get_currency(obj)`, `DEFAULT_CURRENCY` |
| **Time zone** (aware datetimes) | `TEMPLATES_PRO["TIME_ZONE"]`, Django's `TIME_ZONE` when `USE_TZ` is on |

So one template serves customers in several countries. The demo's invoice
shows `£1,234.50` and `15 Jan 2026` for a British customer and `1.234,50 €`
and `15.01.2026` for a German one, with no change to the template.

### From chip to output

1. The editor stores the choice on the chip as JSON:
   `<span data-tp="var" data-path="invoice.total" data-format='{"kind":"money","currency":"EUR"}'>`.
2. On save, the compiler validates it (known `kind`, known `style`, simple
   values only) and writes `{{ tp_format(invoice["total"], "…spec…") }}`.
3. At render time `tp_format` calls `format_value()` with the document's
   locale, currency and time zone.

### Values that don't fit

- **Empty values.** `None`, `""` and missing keys print the fallback, or
  nothing. `0` and `False` are values, not empty.
- **Wrong type.** A value that cannot be formatted as asked (text in a
  `money` chip) is printed unchanged, and a warning is logged.
- **Dates as text.** ISO strings such as `"2026-01-15"` are accepted for
  date and time kinds.
- **Booleans.** For non-boolean values, `1`, `true`, `yes` and `y` count as
  yes.
- **`auto`.** A chip with no kind (possible in a block shared by all types,
  where the schema is not known) is formatted by its Python type: dates as
  dates, numbers as numbers, booleans as Yes/No. A money amount is then just
  a number, so in such a block set the format on the chip, or tick the
  block's template types.

File name patterns (`invoice-{invoice.number}`) do not use formats. Dates
there are written as `2026-01-15`, other values as plain text.

## Format options

| `kind` | Options | Example (en_GB) |
|---|---|---|
| `text` | `case`: `none` · `upper` · `lower` · `title` · `capitalize` | `JANE ROE` |
| `number` | `decimals`: 0–10 (empty = automatic) | `1,234.5` |
| `money` | `currency` (ISO code, default from settings/type), `decimals`, `symbol`: `"code"` for `GBP 1,234.50` | `£1,234.50` |
| `percent` | `decimals`; the value is a fraction (`0.175`) | `17.5%` |
| `date` | `style`: `short` · `medium` · `long` · `full`, or `pattern` | `15 January 2026` |
| `datetime` | same as date | `15 Jan 2026, 14:30:00` |
| `time` | same; default `short` | `14:30` |
| `boolean` | `true`, `false` labels | `Paid` |
| `auto` | inferred from the Python value | |

Every kind accepts `fallback`: text shown when the value is `None`, `""` or
missing.

When `decimals` is not set, numbers keep up to three decimals (`1,234.568`),
percentages are rounded to whole numbers (`0.175` → `18%`), and money uses the
currency's usual number of decimals.

The same value in different locales:

| Value | Format | en_GB | de_DE | he_IL |
|---|---|---|---|---|
| `Decimal("1234.5")` | `{"kind": "money"}`, currency GBP / EUR / ILS | `£1,234.50` | `1.234,50 €` | `1,234.50 ₪` |
| `Decimal("1234.5")` | `{"kind": "money", "symbol": "code"}` | `GBP 1,234.50` | `1.234,50 EUR` | `1,234.50 ILS` |
| `Decimal("1234.5")` | `{"kind": "number", "decimals": 2}` | `1,234.50` | `1.234,50` | `1,234.50` |
| `date(2026, 1, 15)` | `{"kind": "date", "style": "long"}` | `15 January 2026` | `15. Januar 2026` | `15 בינואר 2026` |
| `False` | `{"kind": "boolean", "true": "Paid", "false": "Payment due"}` | `Payment due` | `Payment due` | `Payment due` |

Yes/No labels and fallback texts are written by the template author, so they
are not translated.

## Date patterns

Patterns use Unicode CLDR syntax (the same as ICU, Java and Babel):

| Pattern | Output |
|---|---|
| `dd/MM/yyyy` | `15/01/2026` |
| `d MMM y` | `15 Jan 2026` |
| `EEEE, d MMMM y` | `Thursday, 15 January 2026` |
| `MMMM yyyy` | `January 2026` |
| `HH:mm` | `14:30` |
| `h:mm a` | `2:30 PM` |
| `'Q'Q yyyy` | `Q1 2026` |

Quote literal text with single quotes. Month and day names follow the locale
(`de_DE` gives `Donnerstag, 15. Januar 2026`).

## Time zones

Aware datetimes are converted to `TEMPLATES_PRO["TIME_ZONE"]` (default: Django
`TIME_ZONE` when `USE_TZ` is on) before formatting. This applies to dates too,
so a UTC timestamp just after midnight shows the local date.

## Using the formatter in code

```python
from templates_pro.core.formatting import format_value
format_value(Decimal("1234.5"), {"kind": "money", "currency": "EUR"}, locale="de_DE")
# '1.234,50 €'
```
