"""Template types for the demo project (auto-discovered by templates_pro).

Each type declares a schema (what users can insert) and converts real model
instances into plain dicts in build_context().
"""

import datetime as dt
from decimal import Decimal

from templates_pro import Group, ListOf, TemplateType, Var, register

# A group reused by several types, so the shared "customer-details" block works
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


def customer_dict(c):
    return {
        "name": c.name, "company": c.company, "email": c.email, "address": c.address,
        "city": c.city, "country": c.country, "vat_id": c.vat_id,
    }


@register
class InvoiceTemplate(TemplateType):
    key = "invoice"
    label = "Invoice"
    description = "Customer invoices with line items, tax and discount."
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

    def build_context(self, invoice, **kwargs):
        return {
            "invoice": {
                "number": invoice.number, "date": invoice.date, "due_date": invoice.due_date,
                "paid": invoice.paid, "subtotal": invoice.subtotal, "discount": invoice.discount,
                "discount_amount": invoice.discount_amount, "tax_rate": invoice.tax_rate,
                "tax": invoice.tax, "total": invoice.total, "notes": invoice.notes,
                "lines": [
                    {"description": ln.description, "quantity": ln.quantity,
                     "unit_price": ln.unit_price, "amount": ln.amount}
                    for ln in invoice.lines.all()
                ],
            },
            "customer": customer_dict(invoice.customer),
        }

    def get_locale(self, invoice=None):
        return invoice.customer.language if invoice is not None else None

    def get_currency(self, invoice=None):
        return invoice.currency if invoice is not None else None


@register
class CustomerLetterTemplate(TemplateType):
    key = "customer_letter"
    label = "Customer letter"
    description = "Letters to customers (welcome, notices, reminders)."
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

    def build_context(self, customer, *, sender=None, **kwargs):
        open_invoices = [i for i in customer.invoices.all() if not i.paid]
        first = customer.invoices.order_by("date").first()
        return {
            "customer": customer_dict(customer),
            "sender": {"name": getattr(sender, "get_full_name", lambda: "")() or "Sam Taylor",
                       "title": "Account Manager"},
            "account": {
                "since": first.date if first else None,
                "open_invoices": len(open_invoices),
                "balance": sum((i.total for i in open_invoices), Decimal("0")),
            },
        }

    def get_locale(self, customer=None):
        return customer.language if customer is not None else None


@register
class OrderConfirmationTemplate(TemplateType):
    key = "order_confirmation"
    label = "Order confirmation"
    description = "Sent after checkout; works well as HTML email and plain text."
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

    def build_context(self, order, **kwargs):
        items = [{"product": i.product, "quantity": i.quantity, "price": i.price,
                  "line_total": i.price * i.quantity} for i in order.items.all()]
        return {
            "order": {
                "number": order.number, "placed_at": order.placed_at,
                "shipping_method": order.shipping_method,
                "estimated_delivery": order.estimated_delivery,
                "item_count": sum(i["quantity"] for i in items),
                "total": sum((i["line_total"] for i in items), Decimal("0")),
                "items": items,
            },
            "customer": customer_dict(order.customer),
        }

    def get_locale(self, order=None):
        return order.customer.language if order is not None else None


@register
class EmploymentCertificateTemplate(TemplateType):
    key = "employment_certificate"
    label = "Employment certificate"
    description = "HR letter confirming employment."
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

    def build_context(self, employee, **kwargs):
        end = employee.end_date or dt.date.today()
        return {
            "employee": {
                "first_name": employee.first_name, "last_name": employee.last_name,
                "position": employee.position, "department": employee.department,
                "start_date": employee.start_date, "end_date": employee.end_date,
                "is_current": employee.end_date is None,
                "years": (end - employee.start_date).days // 365,
            },
            "manager": {"name": "Robin Ellis", "title": "Head of People"},
        }
