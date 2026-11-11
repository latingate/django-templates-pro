"""Load starter content: sample constants, shared blocks and document templates.

Add "templates_pro.samples" to INSTALLED_APPS (it registers the sample template
types), then:

    python manage.py templates_pro_samples               # create what is missing
    python manage.py templates_pro_samples --overwrite   # reset the samples to the shipped version
    python manage.py templates_pro_samples --remove      # delete the sample templates and blocks

Everything created has a "sample-" slug. Existing constants are never changed.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from templates_pro.samples.loader import SamplesNotInstalled, load_samples, remove_samples


class Command(BaseCommand):
    help = "Load (or remove) the sample document templates, blocks and constants."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--overwrite", action="store_true",
                           help="Reset existing sample blocks and templates to the shipped version")
        group.add_argument("--remove", action="store_true",
                           help="Delete the sample templates and blocks (constants are kept)")

    def handle(self, *args, overwrite=False, remove=False, **options):
        if remove:
            out = remove_samples()
            for item in out.kept:
                self.stdout.write(self.style.WARNING(f"Kept {item}: still used by your content."))
            self.stdout.write(self.style.SUCCESS(f"Removed {len(out.removed)} sample item(s)."))
            self.stdout.write('Constants were kept. You can now take "templates_pro.samples" '
                              "out of INSTALLED_APPS.")
            return
        try:
            out = load_samples(overwrite=overwrite)
        except SamplesNotInstalled as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"Samples ready: {len(out.created)} created, {len(out.updated)} updated, "
            f"{len(out.skipped)} already there."))
        if out.skipped and not overwrite:
            self.stdout.write("Existing items were left as they are "
                              "(--overwrite resets sample blocks and templates).")
        self.stdout.write("Open the admin, go to Document templates, and use the preview links.")
