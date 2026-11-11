from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TemplatesProConfig(AppConfig):
    name = "templates_pro"
    label = "templates_pro"
    verbose_name = _("Document templates")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.utils.module_loading import autodiscover_modules

        from . import checks, engines, signals  # noqa: F401

        engines.configure()

        # Each installed app may define its template types in doctemplate_types.py
        autodiscover_modules("doctemplate_types")
