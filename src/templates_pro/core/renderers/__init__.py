"""Output renderers: turn rendered HTML into HTML / PDF / DOCX / TXT bytes.

Add your own with :func:`register_renderer`::

    from templates_pro.core.renderers import Renderer, register_renderer

    class MarkdownRenderer(Renderer):
        name, mimetype, extension = "md", "text/markdown", "md"
        def render(self, doc):
            ...
            return text.encode()

    register_renderer(MarkdownRenderer())
"""

from __future__ import annotations

import html as _html
from collections.abc import Callable
from dataclasses import dataclass, field

PAGE_SIZES = ("A3", "A4", "A5", "Letter", "Legal")


class RendererUnavailable(RuntimeError):
    """Raised when an optional dependency (WeasyPrint, python-docx) is missing."""


@dataclass
class PageSettings:
    size: str = "A4"
    orientation: str = "portrait"  # or "landscape"
    #: CSS margin shorthand, e.g. "20mm" or "25mm 18mm 20mm 18mm"
    margin: str = "20mm"


@dataclass
class RenderInput:
    body_html: str
    title: str = "Document"
    css: str = ""
    header_html: str = ""
    footer_html: str = ""
    page: PageSettings = field(default_factory=PageSettings)
    lang: str = "en"
    base_url: str | None = None
    #: WeasyPrint-compatible url_fetcher (also used by the DOCX renderer for images)
    url_fetcher: Callable | None = None


class Renderer:
    name = ""
    mimetype = "application/octet-stream"
    extension = ""
    label = ""

    def is_available(self) -> bool:
        return True

    def render(self, doc: RenderInput) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


BASE_CSS = """
.tp-document img { max-width: 100%; height: auto; }
.tp-document table { border-collapse: collapse; width: 100%; }
.tp-document table p { margin: 0; }
.tp-document td, .tp-document th { vertical-align: top; }
.tp-running-header, .tp-running-footer { font-size: 9pt; }
"""

PRINT_CSS = """
@page {{ size: {size} {orientation}; margin: {margin};
  @top-center {{ content: element(tpHeader); width: 100%; }}
  @bottom-center {{ content: element(tpFooter); width: 100%; }} }}
.tp-running-header {{ position: running(tpHeader); }}
.tp-running-footer {{ position: running(tpFooter); }}
.tp-page-number::after {{ content: counter(page); }}
.tp-page-count::after {{ content: counter(pages); }}
"""


def build_document_html(doc: RenderInput, *, for_print: bool = False) -> str:
    css = BASE_CSS + doc.css
    if for_print:
        css = PRINT_CSS.format(
            size=doc.page.size, orientation=doc.page.orientation, margin=doc.page.margin
        ) + css
    header = f'<header class="tp-running-header">{doc.header_html}</header>' if doc.header_html else ""
    footer = f'<footer class="tp-running-footer">{doc.footer_html}</footer>' if doc.footer_html else ""
    # Running elements must precede the content in print; in screen HTML the
    # footer goes after the body like a normal page footer.
    if for_print:
        body = f'{header}{footer}<main class="tp-document">{doc.body_html}</main>'
    else:
        body = f'{header}<main class="tp-document">{doc.body_html}</main>{footer}'
    return (
        f'<!DOCTYPE html>\n<html lang="{_html.escape(doc.lang)}"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_html.escape(doc.title)}</title><style>{css}</style></head>"
        f'<body class="tp-body">{body}</body></html>'
    )


_REGISTRY: dict[str, Renderer] = {}


def register_renderer(renderer: Renderer) -> Renderer:
    _REGISTRY[renderer.name] = renderer
    return renderer


def get_renderer(name: str) -> Renderer:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"No renderer registered for format {name!r}") from None


def all_renderers() -> dict[str, Renderer]:
    return dict(_REGISTRY)


def _register_builtins():
    from .docx import DocxRenderer
    from .html import HtmlRenderer
    from .pdf import PdfRenderer
    from .txt import TxtRenderer

    for r in (HtmlRenderer(), PdfRenderer(), DocxRenderer(), TxtRenderer()):
        register_renderer(r)


_register_builtins()
