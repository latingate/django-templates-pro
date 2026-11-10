# HTML contract

The editor (`frontend/src/extensions.js`) and the compiler
(`src/templates_pro/core/compiler.py`) agree on this markup. It is what is
stored in `DocumentTemplate.body` and `TemplateBlock.body`, so you can also
generate templates programmatically. See `example/demo/samples/` for full
examples.

| Element | Markup | Compiles to |
|---|---|---|
| Variable | `<span data-tp="var" data-path="invoice.total" data-format='{"kind":"money"}'>Total</span>` | `{{ tp_format(invoice["total"], "…spec…") }}` |
| Constant | `<span data-tp="const" data-key="company_name">Company</span>` | `{{ tp_format(const["company_name"], "…") }}` |
| Dynamic value | `<span data-tp="dynamic" data-key="today" data-format='{"kind":"date","style":"long"}'>Today</span>` | `{{ tp_format(tp_today, "…") }}` |
| Page number | `<span data-tp="dynamic" data-key="page_number">…</span>` | `<span class="tp-page-number"></span>` |
| Block | `<div data-tp="block" data-slug="company-letterhead"></div>` | `{% include "block:company-letterhead" %}` |
| Repeat section | `<div data-tp="repeat" data-path="order.items" data-as="item">…</div>` | `{% for item in tp_iter(order["items"]) %}…{% endfor %}` |
| Repeated row | `<tr data-tp-repeat="invoice.lines" data-tp-as="line">…</tr>` | `{% for line in … %}<tr>…</tr>{% endfor %}` |
| Condition | `<div data-tp="if" data-path="invoice.discount" data-op="gt" data-value="0">…</div>` | `{% if tp_test(invoice["discount"], "gt", "0") %}…{% endif %}` |

Rules:

- A chip's inner text is only its label. It is ignored when rendering and
  kept for readability.
- `data-format` is a JSON object (see [formatting.md](formatting.md)). Omit it
  to use the schema default.
- Inside a repeat, paths may start with the alias (`line.amount`). Aliases
  must be identifiers, cannot be `const`, `loop` or `tp_*`, and cannot equal a
  schema root.
- Condition operators: `truthy`, `falsy`, `eq`, `ne`, `gt`, `gte`, `lt`,
  `lte`, `contains`. Numeric comparison is used when both sides are numbers.
- Anything else is ordinary rich text filtered by the allowlist (see
  [security.md](security.md#4-html-sanitising)).

Use the compiler directly:

```python
from templates_pro.core.compiler import compile_html, sanitize_html

result = compile_html(html, schema=get_type("invoice").schema, blocks={"footer"}, constants={"company_name"})
result.ok, result.errors, result.warnings
result.variables     # {"invoice.total", "invoice.lines[].amount", ...}
result.source        # the Jinja source
```
