from __future__ import annotations

import re

from . import Renderer, RenderInput


class TxtRenderer(Renderer):
    """Plain text via html2text.

    Output is readable plain text with light Markdown conventions (``#``
    headings, ``*`` bullets, pipe tables). Subclass and change :attr:`options`
    to tune it, then register your subclass under the name ``"txt"``.
    """

    name = "txt"
    mimetype = "text/plain; charset=utf-8"
    extension = "txt"
    label = "Plain text"

    options = {
        "body_width": 0,
        "ignore_images": True,
        "ignore_emphasis": True,
        "ignore_links": False,
        "inline_links": True,
        "unicode_snob": True,
        "single_line_break": False,
    }

    def to_text(self, html: str) -> str:
        import html2text

        h = html2text.HTML2Text()
        for key, value in self.options.items():
            setattr(h, key, value)
        return h.handle(html)

    def render(self, doc: RenderInput) -> bytes:
        parts = [doc.header_html, doc.body_html, doc.footer_html]
        text = "\n\n".join(self.to_text(p).strip() for p in parts if p and p.strip())
        text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
        return text.encode("utf-8")
