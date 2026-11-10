"""Re-compile and validate all blocks and templates.

Run after changing a template type's schema, renaming variables, or upgrading:

    python manage.py templates_pro_validate          # report problems
    python manage.py templates_pro_validate --save   # also refresh compiled sources
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from templates_pro.models import DocumentTemplate, TemplateBlock


class Command(BaseCommand):
    help = "Validate (and optionally re-compile) all document templates and blocks."

    def add_arguments(self, parser):
        parser.add_argument("--save", action="store_true", help="Re-save to refresh compiled code")

    def handle(self, *args, save=False, **options):
        problems = 0
        for obj in [*TemplateBlock.objects.all(), *DocumentTemplate.objects.all()]:
            label = f"{type(obj)._meta.verbose_name} “{obj}” ({obj.slug})"
            try:
                obj.full_clean()
            except ValidationError as exc:
                problems += 1
                self.stdout.write(self.style.ERROR(f"✗ {label}"))
                for field, errs in exc.message_dict.items():
                    for e in errs:
                        self.stdout.write(f"    {field}: {e}")
                continue
            if save:
                obj.save()
            self.stdout.write(self.style.SUCCESS(f"✓ {label}"))
        if problems:
            self.stdout.write(self.style.WARNING(f"{problems} item(s) need attention."))
        else:
            self.stdout.write(self.style.SUCCESS("All templates and blocks are valid."))
