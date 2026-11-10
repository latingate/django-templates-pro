"""Ordinary project models. django-templates-pro never sees them directly:
the template types in doctemplate_types.py convert them to plain dicts."""

from decimal import Decimal

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    email = models.EmailField()
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    vat_id = models.CharField("VAT ID", max_length=40, blank=True)
    language = models.CharField(max_length=10, default="en_GB",
                                help_text="Documents for this customer use this locale.")

    def __str__(self):
        return self.company or self.name


class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    due_date = models.DateField()
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.20"))
    discount = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0"))
    currency = models.CharField(max_length=3, default="GBP")
    paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.number

    @property
    def subtotal(self):
        return sum((line.amount for line in self.lines.all()), Decimal("0"))

    @property
    def discount_amount(self):
        return (self.subtotal * self.discount).quantize(Decimal("0.01"))

    @property
    def tax(self):
        return ((self.subtotal - self.discount_amount) * self.tax_rate).quantize(Decimal("0.01"))

    @property
    def total(self):
        return self.subtotal - self.discount_amount + self.tax


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def amount(self):
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    number = models.CharField(max_length=30, unique=True)
    placed_at = models.DateTimeField()
    shipping_method = models.CharField(max_length=100)
    estimated_delivery = models.DateField()

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)


class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
