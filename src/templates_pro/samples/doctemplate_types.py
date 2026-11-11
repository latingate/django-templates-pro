"""Sample template types (auto-discovered when ``templates_pro.samples`` is installed).

They have no ``build_context()``: the default one accepts a plain dict, so
``services.render("sample_invoice", data={...})`` works without any models.
Copy a class into your own ``doctemplate_types.py`` as a starting point, give it
your own ``key``, and write a ``build_context()`` for your models.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.utils.translation import gettext_lazy as _

from templates_pro import Group, ListOf, TemplateType, Var, register

# A group reused by several types, so the shared "customer details" block works
# in invoices, letters and order confirmations alike.
CUSTOMER = Group("Customer", {
    "name": Var("string", "Contact name", sample="Jane Roe"),
    "company": Var("string", "Company", sample="Roe & Partners Ltd"),
    "email": Var("email", "Email", sample="jane@roe-partners.example"),
    "address": Var("string", "Street address", sample="12 Harbour Street"),
    "city": Var("string", "City", sample="Bristol"),
    "country": Var("string", "Country", sample="United Kingdom"),
    "vat_id": Var("string", "VAT ID", sample="GB123456789"),
})


@register
class SampleInvoice(TemplateType):
    key = "sample_invoice"
    label = _("Invoice (sample)")
    description = _("Customer invoices with line items, tax and discount.")
    filename = "invoice-{invoice.number}"
    schema = {
        "invoice": Group("Invoice", {
            "number": Var("string", "Invoice number", sample="INV-2026-0042"),
            "date": Var("date", "Invoice date", sample=dt.date(2026, 1, 15)),
            "due_date": Var("date", "Due date", sample=dt.date(2026, 2, 14)),
            "paid": Var("boolean", "Paid", sample=False,
                        format={"kind": "boolean", "true": "Paid", "false": "Payment due"}),
            "subtotal": Var("money", "Subtotal", sample=Decimal("2350.00")),
            "discount": Var("percent", "Discount rate", sample=Decimal("0.05")),
            "discount_amount": Var("money", "Discount amount", sample=Decimal("117.50")),
            "tax_rate": Var("percent", "Tax rate", sample=Decimal("0.20")),
            "tax": Var("money", "Tax", sample=Decimal("446.50")),
            "total": Var("money", "Total", sample=Decimal("2679.00")),
            "notes": Var("text", "Notes", sample="Thank you for your business."),
            "lines": ListOf("Line items", {
                "description": Var("string", "Description"),
                "quantity": Var("number", "Quantity", format={"kind": "number"}),
                "unit_price": Var("money", "Unit price"),
                "amount": Var("money", "Amount"),
            }, sample=[
                {"description": "Brand workshop (half day)", "quantity": Decimal("1"),
                 "unit_price": Decimal("850.00"), "amount": Decimal("850.00")},
                {"description": "Logo design", "quantity": Decimal("1"),
                 "unit_price": Decimal("1100.00"), "amount": Decimal("1100.00")},
                {"description": "Print-ready files", "quantity": Decimal("4"),
                 "unit_price": Decimal("100.00"), "amount": Decimal("400.00")},
            ]),
        }),
        "customer": CUSTOMER,
    }


@register
class SampleLetter(TemplateType):
    key = "sample_letter"
    label = _("Customer letter (sample)")
    description = _("Letters to customers (welcome, notices, reminders).")
    filename = "letter-{customer.company}"
    schema = {
        "customer": CUSTOMER,
        "sender": Group("Sender", {
            "name": Var("string", "Sender name", sample="Sam Taylor"),
            "title": Var("string", "Sender job title", sample="Account Manager"),
        }),
        "account": Group("Account", {
            "since": Var("date", "Customer since", sample=dt.date(2024, 5, 2)),
            "open_invoices": Var("integer", "Open invoices", sample=2),
            "balance": Var("money", "Open balance", sample=Decimal("1520.40")),
        }),
    }


@register
class SampleOrder(TemplateType):
    key = "sample_order"
    label = _("Order confirmation (sample)")
    description = _("Sent after checkout; works well as HTML email and plain text.")
    filename = "order-{order.number}"
    schema = {
        "order": Group("Order", {
            "number": Var("string", "Order number", sample="NW-58213"),
            "placed_at": Var("datetime", "Placed at", sample=dt.datetime(2026, 1, 15, 16, 42)),
            "shipping_method": Var("string", "Shipping method", sample="Express (1–2 days)"),
            "estimated_delivery": Var("date", "Estimated delivery", sample=dt.date(2026, 1, 17)),
            "item_count": Var("integer", "Number of items", sample=3),
            "total": Var("money", "Order total", sample=Decimal("184.70")),
            "items": ListOf("Items", {
                "product": Var("string", "Product"),
                "quantity": Var("integer", "Quantity"),
                "price": Var("money", "Price"),
                "line_total": Var("money", "Line total"),
            }, sample=[
                {"product": "Linen notebook A5", "quantity": 2, "price": Decimal("18.50"),
                 "line_total": Decimal("37.00")},
                {"product": "Fountain pen, matte black", "quantity": 1,
                 "price": Decimal("147.70"), "line_total": Decimal("147.70")},
            ]),
        }),
        "customer": CUSTOMER,
    }


@register
class SampleCertificate(TemplateType):
    key = "sample_certificate"
    label = _("Employment certificate (sample)")
    description = _("HR letter confirming employment.")
    filename = "certificate-{employee.last_name}"
    schema = {
        "employee": Group("Employee", {
            "first_name": Var("string", "First name", sample="Alex"),
            "last_name": Var("string", "Last name", sample="Morgan"),
            "position": Var("string", "Position", sample="Senior Designer"),
            "department": Var("string", "Department", sample="Studio"),
            "start_date": Var("date", "Start date", sample=dt.date(2021, 9, 1)),
            "end_date": Var("date", "End date", sample=None),
            "is_current": Var("boolean", "Currently employed", sample=True),
            "years": Var("integer", "Years of service", sample=4),
        }),
        "manager": Group("Signed by", {
            "name": Var("string", "Name", sample="Robin Ellis"),
            "title": Var("string", "Title", sample="Head of People"),
        }),
    }
