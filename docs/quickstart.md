# Quickstart

This takes you from an empty project to a downloadable PDF invoice.

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

- Reuse content with [shared blocks](concepts.md#shared-blocks).
- Embed the editor in your own pages: [editor.md](editor.md).
- Keep an immutable copy of each issued invoice: [`generate()`](rendering.md#storing-generated-documents).
- Run the [demo](../example/README.md) to see every feature in action.
