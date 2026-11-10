"""Public rendering API.

    from templates_pro.services import render, render_to_response, generate

    doc = render("invoice-standard", invoice, fmt="pdf")
    doc.content, doc.mimetype, doc.filename

    return render_to_response("invoice-standard", invoice, fmt="pdf")

    record = generate("invoice-standard", invoice, fmt="pdf", user=request.user)

The first argument may be a :class:`DocumentTemplate`, its slug, or a template
type key (then the type's *default* template is used).
"""

from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass
from typing import Any

from django.core.cache import caches
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Count, Max
from django.http import HttpResponse
from django.utils.module_loading import import_string

from .conf import tp_settings
from .core import engine
from .core.compiler import compile_html
from .core.formatting import normalize_locale
from .core.renderers import PageSettings, RenderInput, get_renderer
from .fetchers import BASE_URL, get_url_fetcher
from .themes import theme_css

__all__ = [
    "RenderedDocument",
    "TemplateNotAvailable",
    "get_template",
    "get_context",
    "get_constants",
    "render",
    "render_body",
    "render_to_response",
    "generate",
    "preview_document",
]


class TemplateNotAvailable(LookupError):
    pass


# ---------------------------------------------------------------------------
# Cache versioning for blocks and constants
# ---------------------------------------------------------------------------

_VERSION_KEYS = {"blocks": "templates_pro:v:blocks", "constants": "templates_pro:v:constants"}


def _cache():
    return caches[tp_settings.CACHE_ALIAS]


def content_version(kind: str) -> str:
    """A token that changes whenever blocks/constants change.

    Stored in the cache; recomputed from the database when the cache is empty
    (or a DummyCache), so it is always correct, just slower without a cache.
    """
    key = _VERSION_KEYS[kind]
    value = _cache().get(key)
    if value is None:
        from .models import SiteConstant, TemplateBlock

        model = TemplateBlock if kind == "blocks" else SiteConstant
        agg = model.objects.aggregate(m=Max("updated_at"), c=Count("pk"))
        value = f"{agg['c']}:{agg['m'].isoformat() if agg['m'] else '-'}"
        _cache().set(key, value, None)
    return value


def bump_version(kind: str) -> None:
    _cache().delete(_VERSION_KEYS[kind])


# ---------------------------------------------------------------------------
# Environment & data
# ---------------------------------------------------------------------------

_env_lock = threading.Lock()
_env: engine.SafeEnvironment | None = None


def _fetch_block(slug: str):
    from .models import TemplateBlock

    row = TemplateBlock.objects.filter(slug=slug).values_list("compiled", "is_active").first()
    if row is None:
        return None
    compiled, active = row
    version = content_version("blocks")
    return (compiled if active else ""), (lambda: content_version("blocks") == version)


def get_environment() -> engine.SafeEnvironment:
    global _env
    if _env is None:
        with _env_lock:
            if _env is None:
                _env = engine.create_environment(fetch_block=_fetch_block)
    return _env


_constants_cache: dict[str, Any] = {"version": None, "values": {}}


def get_constants(request=None) -> dict[str, str]:
    """Active :class:`SiteConstant` values, plus ``CONSTANTS_PROVIDER`` output."""
    from .models import SiteConstant

    version = content_version("constants")
    if _constants_cache["version"] != version:
        _constants_cache["values"] = dict(
            SiteConstant.objects.filter(is_active=True).values_list("key", "value"))
        _constants_cache["version"] = version
    values = dict(_constants_cache["values"])
    if tp_settings.CONSTANTS_PROVIDER:
        provider = import_string(tp_settings.CONSTANTS_PROVIDER)
        values.update(provider(request=request) or {})
    return values


def get_template(ref) -> Any:
    """Resolve a DocumentTemplate from an instance, slug, pk or type key."""
    from .models import DocumentTemplate

    if isinstance(ref, DocumentTemplate):
        return ref
    qs = DocumentTemplate.objects.select_related("header_block", "footer_block")
    if isinstance(ref, int):
        found = qs.filter(pk=ref).first()
    else:
        found = qs.filter(slug=ref).first() or qs.filter(
            template_type=ref, is_default=True, is_active=True).first()
    if found is None:
        raise TemplateNotAvailable(f"No document template matches {ref!r}")
    if not found.is_active:
        raise TemplateNotAvailable(f"Document template {found.slug!r} is inactive")
    return found


def get_context(template, obj=None, *, data: dict | None = None, sample: bool = False,
                **kwargs) -> dict:
    ttype = template.type
    if data is not None:
        return data
    if sample:
        return ttype.sample_context()
    return ttype.build_context(obj, **kwargs)


def _locale_for(template, obj, locale: str | None) -> str:
    if locale:
        return normalize_locale(locale)
    if template.locale:
        return normalize_locale(template.locale)
    try:
        type_locale = template.type.get_locale(obj)
    except Exception:
        type_locale = None
    return normalize_locale(type_locale) if type_locale else tp_settings.locale


def _render_block_source(env, block, ctx) -> str:
    if block is None or not block.is_active:
        return ""
    return engine.render_source(env, block.compiled, ctx, max_output=tp_settings.MAX_OUTPUT_CHARS,
                                timeout=tp_settings.RENDER_TIMEOUT)


def render_body(template, context: dict, *, locale: str = "en_US", now=None,
                request=None, currency: str | None = None) -> tuple[str, str, str]:
    """Render a template's body/header/footer HTML. Returns (body, header, footer)."""
    env = get_environment()
    ctx = engine.build_render_context(
        context, constants=get_constants(request), locale=locale, tz=tp_settings.tzinfo,
        currency=currency or tp_settings.DEFAULT_CURRENCY, now=now)
    limits = {"max_output": tp_settings.MAX_OUTPUT_CHARS, "timeout": tp_settings.RENDER_TIMEOUT}
    body = engine.render_source(env, template.compiled, ctx, **limits)
    header = _render_block_source(env, template.header_block, ctx)
    footer = _render_block_source(env, template.footer_block, ctx)
    return body, header, footer


@dataclass
class RenderedDocument:
    content: bytes
    fmt: str
    mimetype: str
    filename: str
    template: Any = None

    def as_response(self, *, attachment: bool = True) -> HttpResponse:
        response = HttpResponse(self.content, content_type=self.mimetype)
        disposition = "attachment" if attachment else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="{self.filename}"'
        return response

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


def _build_input(template, body, header, footer, locale, fmt) -> RenderInput:
    return RenderInput(
        body_html=body,
        header_html=header,
        footer_html=footer,
        title=template.name,
        css=theme_css(template.theme) + "\n" + (template.extra_css or ""),
        page=PageSettings(size=template.page_size, orientation=template.orientation,
                          margin=template.margin or "20mm"),
        lang=locale.split("_")[0],
        base_url=BASE_URL,
        url_fetcher=get_url_fetcher(fmt),
    )


def render(template, obj=None, *, fmt: str | None = None, data: dict | None = None,
           locale: str | None = None, sample: bool = False, request=None,
           now: dt.datetime | None = None, check_format: bool = True,
           **context_kwargs) -> RenderedDocument:
    """Render ``template`` for ``obj`` (or explicit ``data``) to ``fmt``."""
    template = get_template(template)
    fmt = fmt or (template.output_formats or ["html"])[0]
    if check_format and fmt not in (template.output_formats or []):
        raise TemplateNotAvailable(f"Template {template.slug!r} does not allow format {fmt!r}")
    renderer = get_renderer(fmt)
    context = get_context(template, obj, data=data, sample=sample, **context_kwargs)
    loc = _locale_for(template, obj, locale)
    currency = None
    if obj is not None:
        try:
            currency = template.type.get_currency(obj)
        except Exception:
            currency = None
    body, header, footer = render_body(template, context, locale=loc, now=now, request=request,
                                       currency=currency)
    content = renderer.render(_build_input(template, body, header, footer, loc, fmt))
    pattern = template.filename_pattern or template.type.filename or template.slug
    filename = f"{engine.render_filename(pattern, context, default=template.slug)}.{renderer.extension}"
    return RenderedDocument(content=content, fmt=fmt, mimetype=renderer.mimetype,
                            filename=filename, template=template)


def render_to_response(template, obj=None, *, fmt: str | None = None, attachment: bool = True,
                       **kwargs) -> HttpResponse:
    return render(template, obj, fmt=fmt, **kwargs).as_response(attachment=attachment)


def generate(template, obj=None, *, fmt: str | None = None, user=None, **kwargs):
    """Render and store a :class:`GeneratedDocument` (an immutable record)."""
    from django.contrib.contenttypes.models import ContentType

    from .models import GeneratedDocument

    doc = render(template, obj, fmt=fmt, **kwargs)
    tpl = doc.template
    snapshot_parts = [tpl.compiled]
    for slug in sorted(tpl.all_block_slugs()):
        source = _fetch_block(slug)
        if source:
            snapshot_parts.append(f"{{# block:{slug} #}}\n{source[0]}")
    record = GeneratedDocument(
        template=tpl, template_version=tpl.version, template_type=tpl.template_type,
        format=doc.fmt, filename=doc.filename, size=len(doc.content),
        checksum=GeneratedDocument.sha256(doc.content), snapshot="\n\n".join(snapshot_parts),
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    if obj is not None and hasattr(obj, "_meta") and getattr(obj, "pk", None) is not None:
        record.content_type = ContentType.objects.get_for_model(obj)
        record.object_id = str(obj.pk)
    record.file.save(doc.filename, ContentFile(doc.content), save=False)
    record.save()
    return record


class _Unsaved:
    """A lightweight stand-in for DocumentTemplate used by live previews."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    @property
    def type(self):
        from .registry import get_type

        return get_type(self.template_type)


def preview_document(body: str, template_type: str, *, fmt: str = "html", theme: str | None = None,
                     header_block=None, footer_block=None, page_size: str = "A4",
                     orientation: str = "portrait", margin: str = "20mm", extra_css: str = "",
                     locale: str | None = None, request=None) -> tuple[RenderedDocument | None,
                                                                         list[str]]:
    """Render unsaved editor HTML with sample data. Returns (document, errors)."""
    from .models import TemplateBlock
    from .registry import UnknownTemplateType, get_type

    try:
        ttype = get_type(template_type) if template_type else None
    except UnknownTemplateType as exc:
        return None, [str(exc)]
    known_blocks = set(TemplateBlock.objects.values_list("slug", flat=True))
    result = compile_html(body, schema=ttype.schema if ttype else None,
                          constants=set(get_constants(request)), blocks=known_blocks)
    if result.errors:
        return None, result.errors

    def block(ref):
        if ref in (None, ""):
            return None
        try:
            return TemplateBlock.objects.get(pk=ref) if str(ref).isdigit() else (
                TemplateBlock.objects.get(slug=ref))
        except ObjectDoesNotExist:
            return None

    tpl = _Unsaved(
        name="Preview", slug="preview", template_type=template_type, compiled=result.source,
        theme=theme or tp_settings.DEFAULT_THEME, extra_css=extra_css, page_size=page_size,
        orientation=orientation, margin=margin, header_block=block(header_block),
        footer_block=block(footer_block), locale=locale or "", filename_pattern="preview",
    )
    data = ttype.sample_context() if ttype else {}
    loc = _locale_for(tpl, None, locale)
    try:
        body_html, header, footer = render_body(tpl, data, locale=loc, request=request)
    except engine.TemplateRenderError as exc:
        return None, [str(exc)]
    renderer = get_renderer(fmt)
    content = renderer.render(_build_input(tpl, body_html, header, footer, loc, fmt))
    return RenderedDocument(content=content, fmt=fmt, mimetype=renderer.mimetype,
                            filename=f"preview.{renderer.extension}"), []
