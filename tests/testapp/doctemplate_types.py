import datetime as dt
from decimal import Decimal

from templates_pro import Group, ListOf, TemplateType, Var, register


@register
class InvoiceType(TemplateType):
    key = "invoice"
    label = "Invoice"
    filename = "invoice-{invoice.number}"
    schema = {
        "invoice": Group("Invoice", {
            "number": Var("string", "Number", sample="INV-0042"),
            "date": Var("date", "Date", sample=dt.date(2026, 2, 1)),
            "total": Var("money", "Total", sample=Decimal("1250.50")),
            "discount": Var("percent", "Discount", sample=0.1),
            "lines": ListOf("Lines", {
                "description": Var("string", "Description"),
                "qty": Var("integer", "Quantity"),
                "price": Var("money", "Price"),
            }),
        }),
        "customer": Group("Customer", {"name": Var("string", "Name", sample="Jane Roe")}),
    }

    def build_context(self, obj=None, **kwargs):
        return obj  # tests pass dicts


@register
class LetterType(TemplateType):
    key = "letter"
    label = "Letter"
    schema = {"recipient": Group("Recipient", {"name": Var("string", "Name")})}
