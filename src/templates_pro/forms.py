from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .conf import tp_settings
from .core.renderers import all_renderers
from .models import DocumentTemplate, TemplateBlock
from .registry import type_choices
from .themes import theme_choices
from .widgets import TemplateEditorWidget


def format_choices():
    renderers = all_renderers()
    return [(f, renderers[f].label or f.upper()) for f in tp_settings.OUTPUT_FORMATS
            if f in renderers]


class DocumentTemplateForm(forms.ModelForm):
    template_type = forms.ChoiceField(label=_("Template type"), choices=type_choices)
    theme = forms.ChoiceField(label=_("Theme"), choices=theme_choices)
    output_formats = forms.MultipleChoiceField(
        label=_("Output formats"), choices=format_choices, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = DocumentTemplate
        fields = "__all__"
        widgets = {
            "body": TemplateEditorWidget(type_field="template_type", direction_field="direction",
                                         locale_field="locale"),
            "extra_css": forms.Textarea(attrs={"rows": 4, "style": "font-family: monospace"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show unregistered type keys of existing rows instead of silently changing them.
        current = self.instance.template_type if self.instance and self.instance.pk else None
        choices = list(type_choices())
        if current and current not in dict(choices):
            choices.append((current, f"{current} (unregistered)"))
        self.fields["template_type"].choices = choices
        for name in ("header_block", "footer_block"):
            if name in self.fields:
                self.fields[name].queryset = TemplateBlock.objects.filter(is_active=True)


class TemplateBlockForm(forms.ModelForm):
    template_types = forms.MultipleChoiceField(
        label=_("Template types"), choices=type_choices, required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=TemplateBlock._meta.get_field("template_types").help_text)

    class Meta:
        model = TemplateBlock
        fields = "__all__"
        widgets = {"body": TemplateEditorWidget(types_field="template_types", preset="full",
                                                height=320)}
