"""Load the demo content: constants, shared blocks, templates and sample data.

    python manage.py seed_demo            # create what is missing
    python manage.py seed_demo --reset    # delete demo content first

The sample HTML lives in demo/samples/: it is exactly what the editor stores,
so it doubles as a reference for the chip markup.
"""

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from demo.models import Customer, Employee, Invoice, InvoiceLine, Order, OrderItem
from templates_pro.models import DocumentTemplate, SiteConstant, TemplateBlock

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


class Command(BaseCommand):
    help = "Seed the django-templates-pro demo"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        manifest = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
        if reset:
            DocumentTemplate.objects.all().delete()
            TemplateBlock.objects.all().delete()
            SiteConstant.objects.all().delete()
            for model in (InvoiceLine, Invoice, OrderItem, Order, Customer, Employee):
                model.objects.all().delete()

        for c in manifest["constants"]:
            SiteConstant.objects.update_or_create(key=c["key"], defaults=c)

        # Blocks may include blocks: save in manifest order (dependencies first).
        for b in manifest["blocks"]:
            block, _ = TemplateBlock.objects.get_or_create(slug=b["slug"], defaults={"name": b["name"]})
            block.name, block.category = b["name"], b["category"]
            block.template_types, block.description = b["types"], b["description"]
            block.body = (SAMPLES / "blocks" / f"{b['slug']}.html").read_text(encoding="utf-8")
            block.full_clean()
            block.save()

        for t in manifest["templates"]:
            tpl, _ = DocumentTemplate.objects.get_or_create(
                slug=t["slug"], defaults={"name": t["name"], "template_type": t["type"]})
            tpl.name, tpl.template_type, tpl.theme = t["name"], t["type"], t["theme"]
            tpl.output_formats = t["formats"]
            tpl.is_default = t.get("is_default", False)
            tpl.margin = t.get("margin", "20mm")
            tpl.extra_css = t.get("extra_css", "")
            tpl.footer_block = TemplateBlock.objects.filter(slug=t.get("footer")).first()
            tpl.header_block = TemplateBlock.objects.filter(slug=t.get("header")).first()
            tpl.body = (SAMPLES / "templates" / f"{t['slug']}.html").read_text(encoding="utf-8")
            tpl.full_clean()
            tpl.save()

        if not Customer.objects.exists():
            self.sample_data()

        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write(self.style.WARNING(
                "Created superuser admin / admin (demo only: never do this in production)."))
        self.stdout.write(self.style.SUCCESS(
            f"Demo ready: {SiteConstant.objects.count()} constants, {TemplateBlock.objects.count()} "
            f"blocks, {DocumentTemplate.objects.count()} templates."))

    def sample_data(self):
        jane = Customer.objects.create(
            name="Jane Roe", company="Roe & Partners Ltd", email="jane@roe-partners.example",
            address="12 Harbour Street", city="Bristol", country="United Kingdom",
            vat_id="GB123456789", language="en_GB")
        klaus = Customer.objects.create(
            name="Klaus Becker", company="Becker Möbel GmbH", email="k.becker@moebel.example",
            address="Lindenstraße 8", city="Köln", country="Deutschland", vat_id="DE811111111",
            language="de_DE")
        amelie = Customer.objects.create(
            name="Amélie Durand", company="", email="amelie@durand.example",
            address="3 rue des Lilas", city="Lyon", country="France", language="fr_FR")

        def invoice(customer, number, days_ago, lines, **kw):
            date = dt.date.today() - dt.timedelta(days=days_ago)
            inv = Invoice.objects.create(customer=customer, number=number, date=date,
                                         due_date=date + dt.timedelta(days=30), **kw)
            for desc, qty, price in lines:
                InvoiceLine.objects.create(invoice=inv, description=desc,
                                           quantity=Decimal(qty), unit_price=Decimal(price))

        invoice(jane, "INV-2026-0041", 40, [("Brand workshop (half day)", "1", "850"),
                                              ("Logo design", "1", "1100"),
                                              ("Print-ready files", "4", "100")],
                discount=Decimal("0.05"), notes="Thank you for your business.")
        invoice(jane, "INV-2026-0045", 5, [("Website maintenance, January", "1", "320")])
        invoice(klaus, "INV-2026-0043", 20, [("Katalog-Layout, 24 Seiten", "24", "65"),
                                               ("Bildbearbeitung", "12.5", "48")],
                tax_rate=Decimal("0.19"), paid=True, currency="EUR")
        invoice(amelie, "INV-2026-0044", 12, [("Portrait photography session", "1", "420")],
                tax_rate=Decimal("0.20"), currency="EUR")

        order = Order.objects.create(
            customer=jane, number="NW-58213", placed_at=timezone.now() - dt.timedelta(hours=3),
            shipping_method="Express (1–2 days)",
            estimated_delivery=dt.date.today() + dt.timedelta(days=2))
        OrderItem.objects.create(order=order, product="Linen notebook A5", quantity=2,
                                 price=Decimal("18.50"))
        OrderItem.objects.create(order=order, product="Fountain pen, matte black", quantity=1,
                                 price=Decimal("147.70"))
        order2 = Order.objects.create(
            customer=klaus, number="NW-58214", placed_at=timezone.now() - dt.timedelta(days=1),
            shipping_method="Standard", estimated_delivery=dt.date.today() + dt.timedelta(days=5))
        OrderItem.objects.create(order=order2, product="Desk organiser, oak", quantity=1,
                                 price=Decimal("64.00"))

        Employee.objects.create(first_name="Alex", last_name="Morgan", position="Senior Designer",
                                department="Studio", start_date=dt.date(2021, 9, 1))
        Employee.objects.create(first_name="Priya", last_name="Shah", position="Project Manager",
                                department="Client Services", start_date=dt.date(2019, 3, 4),
                                end_date=dt.date(2025, 6, 30))
