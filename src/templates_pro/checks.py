"""System checks: run with ``manage.py check``."""

from django.core.checks import Error, Tags, Warning, register

from .conf import tp_settings


@register(Tags.compatibility)
def check_templates_pro(app_configs=None, **kwargs):
    from .core.renderers import all_renderers
    from .registry import all_types
    from .themes import all_themes, theme_exists

    messages = []
    renderers = all_renderers()
    for fmt in tp_settings.OUTPUT_FORMATS:
        renderer = renderers.get(fmt)
        if renderer is None:
            messages.append(Error(
                f"TEMPLATES_PRO['OUTPUT_FORMATS'] contains {fmt!r} but no renderer is registered.",
                id="templates_pro.E001"))
        elif not renderer.is_available():
            extra = {"pdf": "pdf", "docx": "docx"}.get(fmt, fmt)
            messages.append(Warning(
                f"Output format {fmt!r} is enabled but its library is not installed.",
                hint=f"pip install 'django-templates-pro[{extra}]' or remove {fmt!r} from "
                     "TEMPLATES_PRO['OUTPUT_FORMATS'].",
                id="templates_pro.W001"))
    for fmt in tp_settings.DEFAULT_OUTPUT_FORMATS:
        if fmt not in tp_settings.OUTPUT_FORMATS:
            messages.append(Error(
                f"DEFAULT_OUTPUT_FORMATS contains {fmt!r}, which is not in OUTPUT_FORMATS.",
                id="templates_pro.E002"))
    for key in all_themes():
        if not theme_exists(key):
            messages.append(Error(f"Theme {key!r}: CSS file not found.", id="templates_pro.E003"))
    if tp_settings.DEFAULT_THEME not in all_themes():
        messages.append(Error(f"DEFAULT_THEME {tp_settings.DEFAULT_THEME!r} is not a known theme.",
                              id="templates_pro.E004"))
    if not all_types():
        messages.append(Warning(
            "No document template types are registered.",
            hint="Create a doctemplate_types.py module in one of your apps; see docs/quickstart.md.",
            id="templates_pro.W002"))
    return messages
