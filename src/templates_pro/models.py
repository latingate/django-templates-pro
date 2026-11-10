from __future__ import annotations

import hashlib

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .conf import tp_settings
from .core.compiler import compile_html, find_cycle, sanitize_html, validate_recorded
from .core.renderers import PAGE_SIZES

identifier_validator = RegexValidator(
    r"^[A-Za-z_][A-Za-z0-9_]*$",
    _("Use letters, digits and underscores; do not start with a digit."),
)


def default_output_formats():
    return list(tp_settings.DEFAULT_OUTPUT_FORMATS)


def default_theme():
    return tp_settings.DEFAULT_THEME


def default_page_size():
    return tp_settings.DEFAULT_PAGE_SIZE


def default_margin():
    return tp_settings.DEFAULT_MARGIN


def generated_storage():
    from django.core.files.storage import default_storage, storages

    alias = tp_settings.STORAGE
    return storages[alias] if alias else default_storage


def generated_upload_to(instance, filename):
    from django.utils import timezone

    return timezone.now().strftime(tp_settings.UPLOAD_TO) + filename


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated"), auto_now=True)

    class Meta:
        abstract = True


def _messages(errors: list[str]) -> list[ValidationError]:
    return [ValidationError(e) for e in errors]


class SiteConstant(TimeStampedModel):
    """A predefined value such as the website name, inserted with constant chips."""

    key = models.CharField(_("key"), max_length=64, unique=True,
                           validators=[identifier_validator])
    label = models.CharField(_("label"), max_length=200)
    value = models.TextField(_("value"), blank=True)
    description = models.CharField(_("description"), max_length=255, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["label"]
        verbose_name = _("constant")
        verbose_name_plural = _("constants")

    def __str__(self):
        return f"{self.label} ({self.key})"


class TemplateBlock(TimeStampedModel):
    """A reusable piece of content (header, footer, customer details...).

    Templates include blocks by slug; editing a block changes every template
    that uses it, at render time.
    """

    CATEGORY_CHOICES = [
        ("header", _("Header")),
        ("footer", _("Footer")),
        ("content", _("Content")),
        ("signature", _("Signature")),
        ("other", _("Other")),
    ]

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=100, unique=True,
                            help_text=_("Used to reference the block; avoid renaming."))
    category = models.CharField(_("category"), max_length=20, choices=CATEGORY_CHOICES,
                                default="content")
    description = models.TextField(_("description"), blank=True)
    template_types = models.JSONField(
        _("template types"), default=list, blank=True,
        help_text=_("Types whose variables this block may use. Empty: shared by all types "
                    "(then only use variables every including template provides)."),
    )
    body = models.TextField(_("content"), blank=True)
    compiled = models.TextField(editable=False, blank=True)
    variables = models.JSONField(editable=False, default=list, blank=True)
    includes = models.JSONField(editable=False, default=list, blank=True)
    constants_used = models.JSONField(editable=False, default=list, blank=True)
    is_active = models.BooleanField(
        _("active"), default=True, help_text=_("Inactive blocks render as empty."))

    class Meta:
        ordering = ["category", "name"]
        verbose_name = _("block")
        verbose_name_plural = _("blocks")

    def __str__(self):
        return self.name

    # -- compilation -------------------------------------------------------
    def schema(self) -> dict | None:
        """Merged schema of the declared template types (None = shared by all types)."""
        from .core.schema import merge_schemas
        from .registry import UnknownTemplateType, get_type

        schemas = []
        for key in self.template_types or []:
            try:
                schemas.append(get_type(key).schema)
            except UnknownTemplateType:
                continue
        return merge_schemas(schemas) if schemas else None

    def compile(self):
        known_blocks = set(TemplateBlock.objects.exclude(pk=self.pk).values_list("slug", flat=True))
        known_consts = _known_constants()
        # With declared types, variables get their schema default formats (money, dates...).
        return compile_html(self.body, schema=self.schema(), constants=known_consts,
                            blocks=known_blocks)

    def clean(self):
        super().clean()
        from .registry import UnknownTemplateType, get_type

        result = self.compile()
        errors = list(result.errors)
        if self.slug in result.blocks:
            errors.append(_("A block cannot include itself."))
        # Validate variables against every type this block declares.
        for key in self.template_types or []:
            try:
                ttype = get_type(key)
            except UnknownTemplateType:
                errors.append(_("Unknown template type %(key)s") % {"key": key})
                continue
            for err in validate_recorded(result.variables, ttype.schema):
                errors.append(f"{ttype.label}: {err}")
        # Detect include cycles across all blocks.
        graph = {b.slug: set(b.includes or []) for b in TemplateBlock.objects.exclude(pk=self.pk)}
        graph[self.slug] = set(result.blocks)
        cycle = find_cycle(graph)
        if cycle:
            errors.append(_("Blocks include each other in a loop: %(c)s") % {"c": " → ".join(cycle)})
        # Renaming a referenced block would break templates.
        if self.pk:
            old = TemplateBlock.objects.filter(pk=self.pk).values_list("slug", flat=True).first()
            if old and old != self.slug and self.used_in(old):
                errors.append(_("This block is used by other templates or blocks; "
                                "its slug cannot change."))
        if errors:
            raise ValidationError({"body": _messages(errors)})

    def save(self, *args, **kwargs):
        self.body = sanitize_html(self.body)
        result = self.compile()
        self.compiled = result.source
        self.variables = sorted(result.variables)
        self.includes = sorted(result.blocks)
        self.constants_used = sorted(result.constants)
        super().save(*args, **kwargs)

    @staticmethod
    def used_in(slug: str) -> dict[str, list]:
        templates = [
            t for t in DocumentTemplate.objects.only("pk", "name", "blocks_used",
                                                     "header_block", "footer_block")
            if slug in (t.blocks_used or [])
        ]
        blocks = [b for b in TemplateBlock.objects.only("pk", "name", "includes")
                  if slug in (b.includes or [])]
        return {"templates": templates, "blocks": blocks} if (templates or blocks) else {}


class DocumentTemplate(TimeStampedModel):
    """A document template of a registered type, rendered to one or more formats."""

    ORIENTATION_CHOICES = [("portrait", _("Portrait")), ("landscape", _("Landscape"))]

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    template_type = models.CharField(_("template type"), max_length=100, db_index=True)
    description = models.TextField(_("description"), blank=True)
    body = models.TextField(_("content"), blank=True)

    output_formats = models.JSONField(_("output formats"), default=default_output_formats)
    theme = models.CharField(_("theme"), max_length=50, default=default_theme)
    locale = models.CharField(
        _("locale"), max_length=20, blank=True,
        help_text=_("e.g. en_US, de_DE, he_IL. Empty: the object's or the site default."))
    filename_pattern = models.CharField(
        _("file name"), max_length=200, blank=True,
        help_text=_("e.g. invoice-{invoice.number}. Empty: the type default."))

    page_size = models.CharField(_("page size"), max_length=10,
                                 choices=[(s, s) for s in PAGE_SIZES], default=default_page_size)
    orientation = models.CharField(_("orientation"), max_length=10, choices=ORIENTATION_CHOICES,
                                   default="portrait")
    margin = models.CharField(_("margins"), max_length=60, default=default_margin,
                              help_text=_("CSS shorthand, e.g. 20mm or 30mm 18mm 25mm 18mm"))
    header_block = models.ForeignKey(
        TemplateBlock, verbose_name=_("page header"), null=True, blank=True,
        on_delete=models.PROTECT, related_name="header_for",
        help_text=_("Repeated at the top of every PDF/DOCX page."))
    footer_block = models.ForeignKey(
        TemplateBlock, verbose_name=_("page footer"), null=True, blank=True,
        on_delete=models.PROTECT, related_name="footer_for",
        help_text=_("Repeated at the bottom of every PDF/DOCX page."))
    extra_css = models.TextField(_("extra CSS"), blank=True,
                                 help_text=_("Applied to HTML and PDF output."))

    compiled = models.TextField(editable=False, blank=True)
    variables = models.JSONField(editable=False, default=list, blank=True)
    blocks_used = models.JSONField(editable=False, default=list, blank=True)
    constants_used = models.JSONField(editable=False, default=list, blank=True)
    version = models.PositiveIntegerField(editable=False, default=1)
    is_default = models.BooleanField(
        _("default for its type"), default=False,
        help_text=_("Used when code renders a type without naming a template."))
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["template_type", "name"]
        verbose_name = _("document template")
        verbose_name_plural = _("document templates")
        constraints = [
            models.UniqueConstraint(fields=["template_type"], condition=Q(is_default=True),
                                    name="templates_pro_one_default_per_type"),
        ]

    def __str__(self):
        return self.name

    @property
    def type(self):
        from .registry import get_type

        return get_type(self.template_type)

    @property
    def type_label(self) -> str:
        from .registry import UnknownTemplateType

        try:
            return str(self.type.label)
        except UnknownTemplateType:
            return f"{self.template_type} (unregistered)"

    # -- compilation -------------------------------------------------------
    def compile(self, schema=None):
        known_blocks = set(TemplateBlock.objects.values_list("slug", flat=True))
        return compile_html(self.body, schema=schema, constants=_known_constants(),
                            blocks=known_blocks)

    def all_block_slugs(self, direct: set[str] | None = None) -> set[str]:
        """Blocks used directly, as header/footer, and transitively."""
        pending = set(direct if direct is not None else self.blocks_used or [])
        for fk in (self.header_block, self.footer_block):
            if fk is not None:
                pending.add(fk.slug)
        index = {b.slug: b for b in TemplateBlock.objects.all()}
        seen: set[str] = set()
        while pending:
            slug = pending.pop()
            if slug in seen:
                continue
            seen.add(slug)
            if slug in index:
                pending.update(index[slug].includes or [])
        return seen

    def clean(self):
        super().clean()
        from .core.renderers import all_renderers
        from .registry import UnknownTemplateType, get_type
        from .themes import theme_exists

        errors: dict[str, list] = {}
        try:
            ttype = get_type(self.template_type)
        except UnknownTemplateType as exc:
            raise ValidationError({"template_type": str(exc)}) from exc
        result = self.compile(schema=ttype.schema)
        body_errors = list(result.errors)
        index = {b.slug: b for b in TemplateBlock.objects.all()}
        for slug in sorted(self.all_block_slugs(set(result.blocks))):
            block = index.get(slug)
            if block is None:
                continue
            for err in validate_recorded(set(block.variables or []), ttype.schema):
                body_errors.append(
                    _("Block “%(b)s”: %(e)s (not provided by %(t)s)")
                    % {"b": block.name, "e": err, "t": ttype.label})
        if body_errors:
            errors["body"] = _messages(body_errors)
        enabled = set(tp_settings.OUTPUT_FORMATS)
        formats = self.output_formats or []
        if not formats:
            errors["output_formats"] = [_("Choose at least one output format.")]
        bad = [f for f in formats if f not in enabled or f not in all_renderers()]
        if bad:
            errors["output_formats"] = [_("Not available: %(f)s") % {"f": ", ".join(bad)}]
        if not theme_exists(self.theme):
            errors["theme"] = [_("Unknown theme %(t)s") % {"t": self.theme}]
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        from .registry import UnknownTemplateType, get_type

        self.body = sanitize_html(self.body)
        try:
            schema = get_type(self.template_type).schema
        except UnknownTemplateType:
            schema = None
        result = self.compile(schema=schema)
        if self.pk and result.source != self.compiled:
            self.version = (self.version or 0) + 1
        self.compiled = result.source
        self.variables = sorted(result.variables)
        self.blocks_used = sorted(result.blocks)
        self.constants_used = sorted(result.constants)
        super().save(*args, **kwargs)


class GeneratedDocument(models.Model):
    """A rendered file kept for the record (see services.generate)."""

    template = models.ForeignKey(DocumentTemplate, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="generated")
    template_version = models.PositiveIntegerField(default=0)
    template_type = models.CharField(max_length=100, db_index=True)
    format = models.CharField(max_length=10)
    file = models.FileField(upload_to=generated_upload_to, storage=generated_storage,
                            max_length=300)
    filename = models.CharField(max_length=200)
    size = models.PositiveIntegerField(default=0)
    checksum = models.CharField(max_length=64, help_text="SHA-256 of the file")
    #: The compiled template (and blocks) used, so the record stays explainable.
    snapshot = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("generated document")
        verbose_name_plural = _("generated documents")
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return self.filename

    @staticmethod
    def sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


def _known_constants() -> set[str]:
    from .services import get_constants

    return set(get_constants().keys())
