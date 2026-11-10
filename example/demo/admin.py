from django.contrib import admin

from .models import Customer, Employee, Invoice, InvoiceLine, Order, OrderItem


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "date", "paid")
    inlines = [InvoiceLineInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "customer", "placed_at")
    inlines = [OrderItemInline]


admin.site.register(Customer)
admin.site.register(Employee)
