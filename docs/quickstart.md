# Quickstart

This takes you from an empty project to a downloadable PDF invoice. You need
`pip install django-templates-pro` and the settings from
[installation.md](installation.md); no system libraries are required.

## Start from the samples (optional)

To see finished templates before writing your own, load the starter content
that ships with the package:

```python
INSTALLED_APPS = [
    # ...
    "templates_pro",
    "templates_pro.samples",     # registers the sample template types
]
```

```bash
python manage.py templates_pro_samples
```

**Admin → Document templates** now lists six templates: three invoices (one
of them Hebrew, right-to-left), a letter, an order confirmation and an
employment certificate. They use seven shared blocks and ten constants. Click
a preview link (HTML, PDF, DOCX…) to see one rendered with sample data, or
open it in the editor and change it.

- Everything created has a `sample-` slug, and the sample types have
  `sample_…` keys, so your own content is never touched.
- Constants (`company_name`, `bank_iban`…) are created only when the key does
  not exist yet. Edit them under **Admin → Constants** to see your own company
  details in every sample.
- The command is safe to re-run: existing items are kept. `--overwrite` resets
  the sample blocks and templates to the shipped version.
- The sample types take plain dicts, so you can render your own data without
  any models:

  ```python
  from templates_pro.services import render_to_response

  render_to_response("sample_invoice", data={"invoice": {...}, "customer": {...}}, fmt="pdf")
  ```

- To start your own type, copy a class from
  `templates_pro/samples/doctemplate_types.py`, give it your own `key` and add
  a `build_context()` (step 1 below).
- When you are done: `python manage.py templates_pro_samples --remove`, then
  take `"templates_pro.samples"` out of `INSTALLED_APPS`. Sample blocks that
  your own templates still use are kept, and so are the constants.

## 1. Declare a template type

A *template type* says what a kind of document can contain and how data gets
in. Put it in `doctemplate_types.py` inside any installed app. It is
auto-discovered, just like `admin.py`.

```python
# billing/doctemplate_types.py
from templates_pro import register, TemplateType, Var, Group, ListOf


@register
class InvoiceTemplate(TemplateType):
    key = "invoice"                         # stored on templates; never change it
    label = "Invoice"
    filename = "invoice-{invoice.number}"   # default download name

    schema = {
        "invoice": Group("Invoice", {
            "number": Var("string", "Invoice number", sample="INV-0042"),
            "date": Var("date", "Invoice date"),
            "total": Var("money", "Total"),
            "lines": ListOf("Line items", {
                "description": Var("string", "Description"),
                "quantity": Var("number", "Quantity"),
                "amount": Var("money", "Amount"),
            }),
        }),
        "customer": Group("Customer", {
            "name": Var("string", "Name", sample="Jane Roe"),
        }),
    }

    def build_context(self, invoice, **kwargs):
        # Plain data only: dicts, lists, str, numbers, Decimal, bool, None, dates.
        return {
            "invoice": {
                "number": invoice.number,
                "date": invoice.date,
                "total": invoice.total,
                "lines": [
                    {"description": l.description, "quantity": l.quantity, "amount": l.amount}
                    for l in invoice.lines.all()
                ],
            },
            "customer": {"name": invoice.customer.name},
        }
```

## 2. Add constants (optional)

**Admin → Constants → Add**: key `company_name`, value `ACME Ltd`. Constants
can be inserted into any template or block.

## 3. Write the template

**Admin → Document templates → Add**

1. Name it, choose **Invoice** as the type, and tick **Default for its type**.
2. In the editor, write the text. To insert data, click **Field**, or type
   `{{` and search. Click an inserted chip to change its format, e.g. a date in
   long style or money in EUR.
3. For line items, insert a table, put the cursor in the second row and open
   **Table → Repeat this row for each item…**, choosing *Line items*. Then
   insert `line › Description` and the other item fields into the row.
4. Click **Preview** to see it with sample data, then **Save**.

## 4. Render it

```python
from django.shortcuts import get_object_or_404
from templates_pro.services import render_to_response

def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render_to_response("invoice", invoice, fmt="pdf")
```

`"invoice"` is the type key, so this renders the type's default template. You
can also pass a template slug or a `DocumentTemplate` instance.

## 5. Next steps

- Writing in Hebrew or Arabic? Set the template's *Locale* (e.g. `he_IL`). Its
  *Text direction* defaults to *Auto*, which makes the document right-to-left:
  see [concepts.md](concepts.md#text-direction-rtl).
- Reuse content with [shared blocks](concepts.md#shared-blocks).
- Embed the editor in your own pages: [editor.md](editor.md).
- Keep an immutable copy of each issued invoice: [`generate()`](rendering.md#storing-generated-documents).
- Run the [demo](../example/README.md) to see every feature in action.
