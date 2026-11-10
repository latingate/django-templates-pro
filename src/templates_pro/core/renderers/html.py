from __future__ import annotations

from . import Renderer, RenderInput, build_document_html


class HtmlRenderer(Renderer):
    name = "html"
    mimetype = "text/html; charset=utf-8"
    extension = "html"
    label = "HTML"

    def render(self, doc: RenderInput) -> bytes:
        return build_document_html(doc).encode("utf-8")
