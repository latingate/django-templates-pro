"""Preview endpoints used by the editor and the admin.

Include in your project URLconf (staff only by default)::

    path("templates-pro/", include("templates_pro.urls")),
"""

from __future__ import annotations

import html
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from .conf import tp_settings
from .core.engine import TemplateRenderError
from .core.renderers import RendererUnavailable, all_renderers
from .models import DocumentTemplate
from .services import preview_document, render


def _check_permission(user):
    perm = tp_settings.PREVIEW_PERMISSION
    if perm and not user.has_perm(perm):
        raise PermissionDenied


def _error_page(errors: list[str], status: int = 200) -> HttpResponse:
    items = "".join(f"<li>{html.escape(str(e))}</li>" for e in errors)
    page = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Preview</title><style>"
        "body{font:14px/1.5 system-ui,sans-serif;margin:2rem;color:#7a1b1b}"
        "h1{font-size:1.1rem}li{margin:.25rem 0}</style></head><body>"
        f"<h1>The template cannot be rendered yet</h1><ul>{items}</ul></body></html>"
    )
    return HttpResponse(page, status=status)


@login_required
@require_POST
def live_preview(request):
    """Render unsaved editor content with sample data (POST JSON or form data)."""
    _check_permission(request.user)
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body or b"{}")
        except ValueError:
            return HttpResponseBadRequest("invalid JSON")
    else:
        payload = request.POST
    fmt = payload.get("fmt") or "html"
    if fmt not in all_renderers() or fmt not in tp_settings.OUTPUT_FORMATS:
        return HttpResponseBadRequest("unknown format")
    try:
        doc, errors = preview_document(
            payload.get("body") or "",
            payload.get("template_type") or "",
            fmt=fmt,
            theme=payload.get("theme") or None,
            header_block=payload.get("header_block") or None,
            footer_block=payload.get("footer_block") or None,
            page_size=payload.get("page_size") or "A4",
            orientation=payload.get("orientation") or "portrait",
            margin=payload.get("margin") or "20mm",
            extra_css=payload.get("extra_css") or "",
            locale=payload.get("locale") or None,
            request=request,
        )
    except RendererUnavailable as exc:
        return _error_page([str(exc)])
    if errors:
        return _error_page(errors)
    return doc.as_response(attachment=fmt not in ("html", "pdf", "txt"))


@login_required
@require_GET
def saved_preview(request, pk: int, fmt: str):
    """Render a saved template with the type's sample data."""
    _check_permission(request.user)
    template = get_object_or_404(DocumentTemplate, pk=pk)
    if fmt not in all_renderers():
        return HttpResponseBadRequest("unknown format")
    try:
        doc = render(template, fmt=fmt, sample=True, request=request, check_format=False)
    except (TemplateRenderError, RendererUnavailable) as exc:
        return _error_page([str(exc)])
    return doc.as_response(attachment=fmt not in ("html", "pdf", "txt"))
