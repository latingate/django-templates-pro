# Formatting reference

Users set formats in the editor by clicking a chip. Underneath, each chip
stores a small JSON *format spec* (`data-format`). Every option below can also
be set as a schema default with `Var(..., format={...})`.

All formatting is done by [Babel](https://babel.pocoo.org/) in the render
locale. Rounding is commercial (half up). Bad values never break a document:
they are printed as-is and a warning is logged to the `templates_pro` logger.

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
