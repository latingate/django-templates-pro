from __future__ import annotations

from django.contrib import admin, messages
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .forms import DocumentTemplateForm, TemplateBlockForm
from .models import DocumentTemplate, GeneratedDocument, SiteConstant, TemplateBlock


def _preview_url(obj, fmt):
    try:
        return reverse("templates_pro:saved_preview", args=[obj.pk, fmt])
    except NoReverseMatch:
        return None


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    form = DocumentTemplateForm
    list_display = ("name", "type_label", "theme", "formats", "is_default", "is_active",
                    "version", "updated_at", "preview_links")
    list_filter = ("template_type", "theme", "is_active", "is_default")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("version", "variables_list", "blocks_list", "updated_at")
    actions = ["duplicate"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "template_type", "description",
                           ("is_active", "is_default"))}),
        (_("Content"), {"fields": ("body",)}),
        (_("Output"), {"fields": ("output_formats", "theme", ("locale", "direction"),
                                  "filename_pattern")}),
        (_("Page"), {"fields": (("page_size", "orientation", "margin"),
                                ("header_block", "footer_block"), "extra_css"),
                     "classes": ("collapse",)}),
        (_("Info"), {"fields": ("version", "updated_at", "variables_list", "blocks_list"),
                     "classes": ("collapse",)}),
    )

    @admin.display(description=_("Type"), ordering="template_type")
    def type_label(self, obj):
        return obj.type_label

    @admin.display(description=_("Formats"))
    def formats(self, obj):
        return ", ".join(f.upper() for f in obj.output_formats or [])

    @admin.display(description=_("Preview"))
    def preview_links(self, obj):
        links = [(u, f.upper()) for f in obj.output_formats or [] if (u := _preview_url(obj, f))]
        return format_html_join(" · ", '<a href="{}" target="_blank">{}</a>', links) or "-"

    @admin.display(description=_("Variables used"))
    def variables_list(self, obj):
        return ", ".join(v.replace("[]", "[*]") for v in obj.variables or []) or "-"

    @admin.display(description=_("Blocks used"))
    def blocks_list(self, obj):
        return ", ".join(sorted(obj.all_block_slugs())) or "-"

    @admin.action(description=_("Duplicate selected templates"))
    def duplicate(self, request, queryset):
        for tpl in queryset:
            base = f"{tpl.slug}-copy"
            slug, n = base, 2
            while DocumentTemplate.objects.filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            tpl.pk, tpl.slug, tpl.is_default = None, slug, False
            tpl.name = f"{tpl.name} (copy)"
            tpl.version = 1
            tpl.save()
        self.message_user(request, _("Duplicated %(n)d template(s).") % {"n": queryset.count()},
                          messages.SUCCESS)


@admin.register(TemplateBlock)
class TemplateBlockAdmin(admin.ModelAdmin):
    form = TemplateBlockForm
    list_display = ("name", "slug", "category", "types", "used_count", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("used_in_list", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "description", "is_active")}),
        (_("Content"), {"fields": ("template_types", "body")}),
        (_("Usage"), {"fields": ("used_in_list", "updated_at")}),
    )

    @admin.display(description=_("Types"))
    def types(self, obj):
        return ", ".join(obj.template_types or []) or _("all")

    @admin.display(description=_("Used by"))
    def used_count(self, obj):
        used = TemplateBlock.used_in(obj.slug)
        return len(used.get("templates", [])) + len(used.get("blocks", [])) if used else 0

    @admin.display(description=_("Used by"))
    def used_in_list(self, obj):
        if not obj.pk:
            return "-"
        used = TemplateBlock.used_in(obj.slug)
        if not used:
            return _("Not used yet")
        items = []
        for t in used.get("templates", []):
            url = reverse("admin:templates_pro_documenttemplate_change", args=[t.pk])
            items.append((url, t.name, _("template")))
        for b in used.get("blocks", []):
            url = reverse("admin:templates_pro_templateblock_change", args=[b.pk])
            items.append((url, b.name, _("block")))
        return format_html("<ul>{}</ul>", format_html_join(
            "", '<li><a href="{}">{}</a> ({})</li>', items))


@admin.register(SiteConstant)
class SiteConstantAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "value", "is_active")
    list_editable = ("value", "is_active")
    search_fields = ("key", "label", "value")


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "template", "format", "size", "created_by", "created_at",
                    "download")
    list_filter = ("format", "template_type")
    search_fields = ("filename", "object_id", "checksum")
    readonly_fields = [f.name for f in GeneratedDocument._meta.fields] + ["download"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description=_("File"))
    def download(self, obj):
        return format_html('<a href="{}">{}</a>', obj.file.url, _("Download")) if obj.file else "-"
