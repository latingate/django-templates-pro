from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TemplatesProSamplesConfig(AppConfig):
    """No models: this app only registers the sample template types.

    ``templates_pro`` autodiscovers ``doctemplate_types.py`` in every installed app,
    including this one.
    """

    name = "templates_pro.samples"
    label = "templates_pro_samples"
    verbose_name = _("Document templates: samples")
