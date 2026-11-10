# Template types

Template types are the developer-facing half of the system. Each project
registers its own; the package itself knows none.

## Where they live

Create `doctemplate_types.py` in any installed app. `templates_pro` imports
these modules at startup (`autodiscover_modules`, like `admin.py`). You can
also call `register()` anywhere that runs at startup, e.g. `AppConfig.ready()`.

## Anatomy

```python
from templates_pro import register, TemplateType, Var, Group, ListOf

@register
class OrderConfirmation(TemplateType):
    key = "order_confirmation"      # stable identifier stored in the database
    label = "Order confirmation"    # shown in the admin and the editor
    description = "Sent after checkout."
    filename = "order-{order.number}"   # default file name (tokens from the context)

    schema = {...}

    def build_context(self, order, **kwargs) -> dict: ...
    def sample_context(self) -> dict: ...          # optional
    def get_locale(self, order=None) -> str | None: ...    # optional
    def get_currency(self, order=None) -> str | None: ...  # optional
```

Do not change `key` once templates exist. If you have to rename one, write a
data migration that updates `DocumentTemplate.template_type` and
`TemplateBlock.template_types`.

## Schema nodes

| Node | Meaning | Editor |
|---|---|---|
| `Var(type, label, sample=None, help="", format=None)` | one value | a chip |
| `Group(label, {name: node, ...}, help="")` | an object | a heading in the picker |
| `ListOf(label, {name: node, ...}, sample=None, sample_count=3)` | a list of objects | repeat sections / repeated rows |

`Var` types are `string`, `text`, `integer`, `number`, `money`, `percent`,
`date`, `datetime`, `time`, `boolean`, `email` and `url`. The type picks the
format options the editor offers and the default format:

| Type | Default format |
|---|---|
| `integer` | number, 0 decimals |
| `number` | number (locale grouping) |
| `money` | money in the default currency |
| `percent` | percent (`0.15` → `15%`) |
| `date` / `datetime` / `time` | medium / medium / short style |
| `boolean` | Yes / No |
| others | text |

Override a default per variable with `format=`, for example
`Var("boolean", "Paid", format={"kind": "boolean", "true": "Paid", "false": "Due"})`.

Names must be identifiers. Root names cannot be `const`, `loop` or anything
starting with `tp_`; `register()` raises `ImproperlyConfigured` otherwise.

### Sharing groups between types

Reuse a `Group` object across types, as in the demo's `CUSTOMER`. A block
that uses `customer.*` then works in every type that has it. Declare the
block's template types accordingly.

## build_context

Called as `build_context(obj, **kwargs)` with whatever you passed to
`render(template, obj, **kwargs)`. It must return **plain data**:

- `dict` (string keys), `list`, `tuple`
- `str`, `int`, `float`, `Decimal`, `bool`, `None`
- `date`, `datetime`, `time`

Anything else, such as a model instance or a QuerySet, raises
`UnsafeContextError` naming the offending path. This rule is a security
boundary (see [security.md](security.md)) and it also keeps queries in your
code where you can optimise them:

```python
def build_context(self, invoice, **kwargs):
    lines = invoice.lines.select_related("product")
    return {"invoice": {..., "lines": [{"description": l.product.name, ...} for l in lines]}}
```

Keys not in the schema are allowed and simply unused. Missing keys render as
empty (or as the chip's fallback text).

You can skip `build_context` by passing data directly:
`render(template, data={...})`.

## sample_context

Used for previews. The default builds data from each `Var.sample`, with
type-appropriate placeholders when a sample is missing, and three generated
items per `ListOf`. Override it for realistic previews, for example by
loading a real record:

```python
def sample_context(self):
    order = Order.objects.order_by("-pk").first()
    return self.build_context(order) if order else super().sample_context()
```

## Locale and currency hooks

```python
def get_locale(self, invoice=None):
    return invoice.customer.language if invoice else None   # e.g. "de_DE"

def get_currency(self, invoice=None):
    return invoice.currency if invoice else None            # e.g. "EUR"
```

Locale precedence is the `locale=` argument, then the template's *Locale*
field, then `get_locale(obj)`, then `TEMPLATES_PRO["DEFAULT_LOCALE"]`, then
`LANGUAGE_CODE`. Currency precedence is the chip's own currency, then
`get_currency(obj)`, then `DEFAULT_CURRENCY`.

## Inspecting the registry

```python
from templates_pro.registry import all_types, get_type, type_choices
get_type("invoice").to_json()      # what the editor receives
```
