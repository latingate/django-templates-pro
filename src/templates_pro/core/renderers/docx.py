"""DOCX via python-docx (``pip install django-templates-pro[docx]``).

Converts the sanitized HTML subset produced by the editor: paragraphs,
headings, inline formatting (bold, italic, underline, strike, sub/sup,
highlight, colour, font size), links, lists (nested), blockquotes, code,
horizontal rules, tables (with colspan), images (data URIs or URLs allowed by
the url_fetcher), page size/orientation/margins, running header/footer and
page number fields.

It is deliberately a *document* converter, not a CSS engine: theme CSS does
not apply to DOCX output. Customize the Word look by subclassing and
overriding :meth:`DocxRenderer.new_document` (e.g. load a ``.docx`` with
your corporate styles).
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from . import PageSettings, Renderer, RendererUnavailable, RenderInput

# ---------------------------------------------------------------------------
# A tiny DOM
# ---------------------------------------------------------------------------

_VOID = {"br", "hr", "img", "col", "wbr"}


@dataclass
class El:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)  # El | str

    def style(self) -> dict[str, str]:
        out = {}
        for decl in (self.attrs.get("style") or "").split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                out[k.strip().lower()] = v.strip()
        return out

    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = El("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = El(tag.lower(), {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(el)
        if el.tag not in _VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(html: str) -> El:
    b = _TreeBuilder()
    b.feed(html or "")
    b.close()
    return b.root


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

_BLOCK = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table",
    "blockquote", "pre", "hr", "main", "header", "footer", "section", "article",
}  # fmt: skip
_PAGE_SIZES_MM = {
    "A3": (297, 420), "A4": (210, 297), "A5": (148, 210),
    "Letter": (215.9, 279.4), "Legal": (215.9, 355.6),
}  # fmt: skip
_COLOR_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def _parse_color(value: str):
    from docx.shared import RGBColor

    if not value:
        return None
    m = _COLOR_RE.search(value)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return RGBColor.from_string(h.upper())
    m = _RGB_RE.search(value)
    if m:
        return RGBColor(*(min(255, int(x)) for x in m.groups()))
    return None


def _parse_length_mm(value: str) -> float | None:
    m = re.match(r"^\s*([\d.]+)\s*(mm|cm|in|pt|px)?\s*$", value or "")
    if not m:
        return None
    n, unit = float(m.group(1)), (m.group(2) or "px")
    return {"mm": n, "cm": n * 10, "in": n * 25.4, "pt": n * 25.4 / 72, "px": n * 25.4 / 96}[unit]


def _font_size_pt(value: str) -> float | None:
    m = re.match(r"^\s*([\d.]+)\s*(pt|px|em|rem)?\s*$", value or "")
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2) or "px"
    return {"pt": n, "px": n * 0.75, "em": n * 11, "rem": n * 11}[unit]


@dataclass
class _Fmt:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    sub: bool = False
    sup: bool = False
    highlight: bool = False
    code: bool = False
    color: object = None
    size: float | None = None
    href: str | None = None

    def with_(self, **kw) -> _Fmt:
        d = dict(self.__dict__)
        d.update(kw)
        return _Fmt(**d)


class _Converter:
    def __init__(self, renderer: DocxRenderer, doc: RenderInput, document):
        self.r = renderer
        self.input = doc
        self.document = document

    # -- paragraphs ------------------------------------------------------
    def new_paragraph(self, container, style: str | None = None):
        p = container.add_paragraph()
        if style:
            try:
                p.style = self.document.styles[style]
            except KeyError:
                pass
        return p

    def apply_block_style(self, p, el: El):
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        align = el.style().get("text-align")
        mapping = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
        }
        if align in mapping:
            p.alignment = mapping[align]

    def blocks(self, container, children, *, list_level=0, list_kind=None, style=None):
        """Convert a list of nodes; inline runs are gathered into paragraphs."""
        pending: list = []

        def flush():
            if pending and any(not isinstance(n, str) or n.strip() for n in pending):
                p = self.new_paragraph(container, style)
                self.inlines(p, pending, _Fmt())
            pending.clear()

        for node in children:
            if isinstance(node, El) and node.tag in _BLOCK:
                flush()
                self.block(container, node, list_level=list_level, list_kind=list_kind,
                           style=style)
            else:
                pending.append(node)
        flush()

    def block(self, container, el: El, *, list_level=0, list_kind=None, style=None):
        tag = el.tag
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            p = self.new_paragraph(container, f"Heading {tag[1]}")
            self.apply_block_style(p, el)
            self.inlines(p, el.children, _Fmt())
        elif tag == "p":
            p = self.new_paragraph(container, style)
            self.apply_block_style(p, el)
            self.inlines(p, el.children, _Fmt())
        elif tag in ("ul", "ol"):
            for li in el.children:
                if isinstance(li, El) and li.tag == "li":
                    self.list_item(container, li, list_level + 1, tag)
        elif tag == "li":
            self.list_item(container, el, list_level + 1, list_kind or "ul")
        elif tag == "blockquote":
            self.blocks(container, el.children, style="Quote")
        elif tag == "pre":
            p = self.new_paragraph(container, style)
            self.inlines(p, el.children, _Fmt(code=True), preserve_ws=True)
        elif tag == "hr":
            p = self.new_paragraph(container)
            self._bottom_border(p)
        elif tag == "table":
            self.table(container, el)
        else:  # div, header, section...
            self.blocks(container, el.children, list_level=list_level, list_kind=list_kind,
                        style=style)

    def list_item(self, container, li: El, level: int, kind: str):
        base = "List Number" if kind == "ol" else "List Bullet"
        style = base if level <= 1 else f"{base} {min(level, 3)}"
        inline, nested = [], []
        for c in li.children:
            if isinstance(c, El) and c.tag in ("ul", "ol"):
                nested.append(c)
            elif isinstance(c, El) and c.tag == "p":
                inline.extend(c.children + [" "])
            else:
                inline.append(c)
        p = self.new_paragraph(container, style)
        self.inlines(p, inline, _Fmt())
        for n in nested:
            for sub in n.children:
                if isinstance(sub, El) and sub.tag == "li":
                    self.list_item(container, sub, level + 1, n.tag)

    def table(self, container, el: El):
        rows: list[El] = []

        def collect(node: El):
            for c in node.children:
                if isinstance(c, El):
                    if c.tag == "tr":
                        rows.append(c)
                    elif c.tag in ("thead", "tbody", "tfoot"):
                        collect(c)

        collect(el)
        if not rows:
            return
        grid = []
        for tr in rows:
            cells = [c for c in tr.children if isinstance(c, El) and c.tag in ("td", "th")]
            grid.append(cells)
        ncols = max(sum(max(1, int(c.attrs.get("colspan") or 1)) for c in r) for r in grid) or 1
        table = container.add_table(rows=len(grid), cols=ncols)
        try:
            table.style = self.document.styles["Table Grid"]
        except KeyError:
            pass
        for ri, cells in enumerate(grid):
            ci = 0
            for cell_el in cells:
                if ci >= ncols:
                    break
                span = max(1, int(cell_el.attrs.get("colspan") or 1))
                cell = table.cell(ri, ci)
                if span > 1 and ci + span - 1 < ncols:
                    cell = cell.merge(table.cell(ri, ci + span - 1))
                # python-docx creates one empty paragraph per cell; reuse it.
                first = cell.paragraphs[0]
                self.blocks(cell, cell_el.children)
                if len(cell.paragraphs) > 1 and not first.text and not first.runs:
                    first._element.getparent().remove(first._element)
                if cell_el.tag == "th":
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.bold = True
                bg = cell_el.style().get("background-color")
                if bg:
                    self._shade(cell, bg)
                ci += span

    # -- inline runs -----------------------------------------------------
    def inlines(self, p, nodes, fmt: _Fmt, preserve_ws: bool = False):
        for node in nodes:
            if isinstance(node, str):
                text = node if preserve_ws else re.sub(r"\s+", " ", node)
                if text:
                    self.add_run(p, text, fmt)
                continue
            tag = node.tag
            st = node.style()
            f = fmt
            if tag in ("strong", "b") or st.get("font-weight") in ("bold", "600", "700", "800"):
                f = f.with_(bold=True)
            if tag in ("em", "i") or st.get("font-style") == "italic":
                f = f.with_(italic=True)
            if tag == "u" or "underline" in st.get("text-decoration", ""):
                f = f.with_(underline=True)
            if tag in ("s", "del") or "line-through" in st.get("text-decoration", ""):
                f = f.with_(strike=True)
            if tag == "sub":
                f = f.with_(sub=True)
            if tag == "sup":
                f = f.with_(sup=True)
            if tag == "mark" or st.get("background-color"):
                f = f.with_(highlight=True)
            if tag == "code":
                f = f.with_(code=True)
            if st.get("color"):
                f = f.with_(color=_parse_color(st["color"]))
            if st.get("font-size"):
                f = f.with_(size=_font_size_pt(st["font-size"]))
            if tag == "a" and node.attrs.get("href"):
                f = f.with_(href=node.attrs["href"])
            if tag == "br":
                p.add_run().add_break()
            elif tag == "img":
                self.image(p, node)
            elif "tp-page-number" in node.classes():
                self.field(p, "PAGE")
            elif "tp-page-count" in node.classes():
                self.field(p, "NUMPAGES")
            elif tag in _BLOCK:
                # block inside inline context (e.g. <p> in <li>): keep flowing
                self.inlines(p, node.children, f, preserve_ws)
                p.add_run().add_break()
            else:
                self.inlines(p, node.children, f, preserve_ws)

    def add_run(self, p, text: str, f: _Fmt):
        from docx.enum.text import WD_COLOR_INDEX
        from docx.shared import Pt

        if f.href:
            return self.hyperlink(p, text, f)
        run = p.add_run(text)
        run.bold = f.bold or None
        run.italic = f.italic or None
        run.underline = f.underline or None
        if f.strike:
            run.font.strike = True
        if f.sub:
            run.font.subscript = True
        if f.sup:
            run.font.superscript = True
        if f.highlight:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        if f.code:
            run.font.name = "Courier New"
        if f.color is not None:
            run.font.color.rgb = f.color
        if f.size:
            run.font.size = Pt(f.size)
        return run

    def hyperlink(self, p, text: str, f: _Fmt):
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        r_id = p.part.relate_to(f.href, RT.HYPERLINK, is_external=True)
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), r_id)
        run = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0563C1")
        u = OxmlElement("w:u")
        u.set(qn("w:val"), "single")
        rpr.append(color)
        rpr.append(u)
        if f.bold:
            rpr.append(OxmlElement("w:b"))
        run.append(rpr)
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        run.append(t)
        link.append(run)
        p._p.append(link)

    def field(self, p, instr: str):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), instr)
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "1"
        r.append(t)
        fld.append(r)
        p._p.append(fld)

    def image(self, p, el: El):
        from docx.shared import Mm

        data = self.r.load_image(el.attrs.get("src", ""), self.input)
        if not data:
            alt = el.attrs.get("alt")
            if alt:
                p.add_run(f"[{alt}]")
            return
        width_mm = None
        w = el.attrs.get("width") or el.style().get("width")
        if w:
            width_mm = _parse_length_mm(str(w))
        max_mm = self.r.content_width_mm(self.input.page)
        width_mm = min(width_mm or max_mm, max_mm)
        try:
            p.add_run().add_picture(io.BytesIO(data), width=Mm(width_mm))
        except Exception:
            p.add_run(f"[{el.attrs.get('alt') or 'image'}]")

    # -- low-level helpers -------------------------------------------------
    def _bottom_border(self, p):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        ppr = p._p.get_or_add_pPr()
        bdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "999999")):
            bottom.set(qn(k), v)
        bdr.append(bottom)
        ppr.append(bdr)

    def _shade(self, cell, color_css: str):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        color = _parse_color(color_css)
        if color is None:
            return
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), str(color))
        cell._tc.get_or_add_tcPr().append(shd)


class DocxRenderer(Renderer):
    name = "docx"
    mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    extension = "docx"
    label = "Word (DOCX)"

    def is_available(self) -> bool:
        try:
            import docx  # noqa: F401
        except ImportError:
            return False
        return True

    def new_document(self, doc: RenderInput):
        """Return a fresh ``docx.Document``. Override to start from a styled .docx."""
        import docx

        return docx.Document()

    def content_width_mm(self, page: PageSettings) -> float:
        w, h = _PAGE_SIZES_MM.get(page.size, _PAGE_SIZES_MM["A4"])
        if page.orientation == "landscape":
            w, h = h, w
        _, right, _, left = self.margins_mm(page)
        return max(20.0, w - left - right)

    @staticmethod
    def margins_mm(page: PageSettings) -> tuple[float, float, float, float]:
        parts = [(_parse_length_mm(p) or 20.0) for p in (page.margin or "20mm").split()]
        if len(parts) == 1:
            parts *= 4
        elif len(parts) == 2:
            parts = [parts[0], parts[1], parts[0], parts[1]]
        elif len(parts) == 3:
            parts = [parts[0], parts[1], parts[2], parts[1]]
        return tuple(parts[:4])  # top, right, bottom, left

    def load_image(self, src: str, doc: RenderInput) -> bytes | None:
        if src.startswith("data:"):
            try:
                return base64.b64decode(src.split(",", 1)[1])
            except Exception:
                return None
        if doc.url_fetcher:
            try:
                res = doc.url_fetcher(src)
            except Exception:
                return None
            if res.get("string") is not None:
                s = res["string"]
                return s if isinstance(s, bytes) else s.encode()
            if res.get("file_obj") is not None:
                return res["file_obj"].read()
        return None

    def setup_page(self, document, page: PageSettings):
        from docx.enum.section import WD_ORIENT
        from docx.shared import Mm

        section = document.sections[0]
        w, h = _PAGE_SIZES_MM.get(page.size, _PAGE_SIZES_MM["A4"])
        if page.orientation == "landscape":
            section.orientation = WD_ORIENT.LANDSCAPE
            w, h = h, w
        section.page_width, section.page_height = Mm(w), Mm(h)
        top, right, bottom, left = self.margins_mm(page)
        section.top_margin, section.right_margin = Mm(top), Mm(right)
        section.bottom_margin, section.left_margin = Mm(bottom), Mm(left)
        return section

    def render(self, doc: RenderInput) -> bytes:
        if not self.is_available():
            raise RendererUnavailable(
                "DOCX output needs python-docx: pip install 'django-templates-pro[docx]'"
            )
        document = self.new_document(doc)
        section = self.setup_page(document, doc.page)
        conv = _Converter(self, doc, document)
        if doc.header_html:
            header = section.header
            header.is_linked_to_previous = False
            conv.blocks(header, parse_html(doc.header_html).children)
            self._drop_leading_empty(header)
        if doc.footer_html:
            footer = section.footer
            footer.is_linked_to_previous = False
            conv.blocks(footer, parse_html(doc.footer_html).children)
            self._drop_leading_empty(footer)
        conv.blocks(document, parse_html(doc.body_html).children)
        document.core_properties.title = doc.title
        buf = io.BytesIO()
        document.save(buf)
        return buf.getvalue()

    @staticmethod
    def _drop_leading_empty(container):
        paras = container.paragraphs
        if len(paras) > 1 and not paras[0].text and not paras[0].runs:
            paras[0]._element.getparent().remove(paras[0]._element)
