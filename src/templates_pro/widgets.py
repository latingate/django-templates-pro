"""The TipTap editor as a Django form widget.

Works in the admin and in your own (non-admin) forms; remember
``{{ form.media }}`` in your page template.

    body = forms.CharField(widget=TemplateEditorWidget(template_type="invoice"))

Options:

``preset``         "full" | "simple" | "minimal" (toolbar richness)
``skin``           "default" | "dark" | "paper" | "compact" (editor look)
``template_type``  fixed type key whose variables the picker offers
``type_field``     name of a form field holding the type key (picker follows it)
``types_field``    name of a multi-select field of type keys (used by blocks)
``height``         editor height in px
``preview``        show the Preview button (needs templates_pro.urls)
``direction``      "ltr" | "rtl" | "auto" (auto: by the locale)
``direction_field`` name of a form field holding the direction (editor follows it)
``locale_field``   name of a form field holding the locale (used when direction is auto)
``toolbar``        explicit list of toolbar items, overriding the preset
"""

from __future__ import annotations

from django import forms
from django.urls import NoReverseMatch, reverse

from .conf import tp_settings
from .core.compiler import DYNAMIC_VALUES
from .core.formatting import CONDITION_OPS, DATE_STYLES, TEXT_CASES

EDITOR_JS = "templates_pro/editor/templates-pro-editor.js"
EDITOR_CSS = "templates_pro/editor/templates-pro-editor.css"

COMMON_CURRENCIES = ["USD", "EUR", "GBP", "ILS", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK",
                     "PLN", "CZK", "INR", "CNY", "BRL", "MXN", "ZAR"]


def editor_config(*, preset=None, skin=None, template_type=None, type_field=None,
                  types_field=None, height=None, preview=True, toolbar=None,
                  placeholder="", direction=None, direction_field=None, locale_field=None) -> dict:
    """Build the JSON config the editor bundle reads (also usable from your own JS pages)."""
    from .models import SiteConstant, TemplateBlock
    from .registry import all_types
    from .themes import theme_choices

    defaults = tp_settings.EDITOR
    preview_url = None
    if preview:
        try:
            preview_url = reverse("templates_pro:preview")
        except NoReverseMatch:
            preview_url = None
    blocks = [
        {"slug": b.slug, "name": b.name, "category": b.category,
         "types": b.template_types or [], "html": b.body}
        for b in TemplateBlock.objects.filter(is_active=True).only(
            "slug", "name", "category", "template_types", "body")
    ]
    constants = [
        {"key": c.key, "label": c.label, "value": c.value}
        for c in SiteConstant.objects.filter(is_active=True).only("key", "label", "value")
    ]
    from .core.formatting import RTL_LANGUAGES
    from .services import get_constants

    db_keys = {c["key"] for c in constants}
    for key, value in get_constants().items():
        if key not in db_keys:
            constants.append({"key": key, "label": key.replace("_", " ").title(),
                              "value": str(value)})
    return {
        "preset": preset or defaults.get("preset", "full"),
        "skin": skin or defaults.get("skin", "default"),
        "height": height or defaults.get("height", 460),
        "toolbar": toolbar,
        "placeholder": str(placeholder or ""),
        "templateType": template_type,
        "direction": direction or "auto",
        "directionField": direction_field,
        "localeField": locale_field,
        "rtlLanguages": sorted(RTL_LANGUAGES),
        "typeField": type_field,
        "typesField": types_field,
        "previewUrl": preview_url,
        "outputFormats": list(tp_settings.OUTPUT_FORMATS),
        "types": [t.to_json() for t in all_types()],
        "blocks": blocks,
        "constants": constants,
        "dynamic": [{"key": k, "label": str(v["label"]), "type": v["type"]}
                    for k, v in DYNAMIC_VALUES.items()],
        "themes": [{"key": k, "label": label} for k, label in theme_choices()],
        "formats": {
            "dateStyles": list(DATE_STYLES),
            "textCases": list(TEXT_CASES),
            "conditionOps": list(CONDITION_OPS),
            "currencies": COMMON_CURRENCIES,
            "defaultCurrency": tp_settings.DEFAULT_CURRENCY,
            "locale": tp_settings.locale,
        },
    }


class TemplateEditorWidget(forms.Textarea):
    template_name = "templates_pro/widgets/editor.html"

    def __init__(self, attrs=None, *, preset=None, skin=None, template_type=None, type_field=None,
                 types_field=None, height=None, preview=True, toolbar=None, placeholder="",
                 direction=None, direction_field=None, locale_field=None):
        super().__init__(attrs)
        self.options = dict(preset=preset, skin=skin, template_type=template_type,
                            type_field=type_field, types_field=types_field, height=height,
                            preview=preview, toolbar=toolbar, placeholder=placeholder,
                            direction=direction, direction_field=direction_field,
                            locale_field=locale_field)

    class Media:
        js = [EDITOR_JS]
        css = {"all": [EDITOR_CSS]}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_id = context["widget"]["attrs"].get("id") or f"id_{name}"
        context["widget"]["tp_config_id"] = f"{widget_id}_tpconfig"
        context["widget"]["tp_config"] = editor_config(**self.options)
        return context
