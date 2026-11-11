"""PDF via Typst: the default PDF engine. Pure pip, no system libraries.

The `typst <https://pypi.org/project/typst/>`_ wheel ships the Typst compiler
for Windows, macOS and Linux, and this package ships fonts with Latin and
Hebrew glyphs (``templates_pro/fonts``), so PDF output works right after
``pip install``. Typst lays out right-to-left text, tables included, natively.

Typst does not read HTML, so :class:`TypstWriter` converts the sanitized HTML
subset the editor produces (the same subset the DOCX renderer handles) into
Typst markup. Security: every piece of document text becomes a Typst *string
literal* (``#"..."``), so no user text is ever parsed as Typst code. Only
values the converter builds itself (colours, sizes, numbers) are emitted as
code, after validation. The compile runs in a temporary root folder holding
only the generated file and its images; Typst has no network access.

Themes are Typst dictionaries of style values (see ``THEMES``), not CSS.
"""

from __future__ import annotations

import base64
import math
import re
import tempfile
from pathlib import Path

from . import PageSettings, Renderer, RendererUnavailable, RenderInput
from .docx import El, parse_html

FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "fonts"

# ---------------------------------------------------------------------------
# Themes: Typst expressions per style key. Unknown themes fall back to "minimal".
# ---------------------------------------------------------------------------

SANS = '("Noto Sans", "Noto Sans Hebrew", "DejaVu Sans")'
SERIF = '("Libertinus Serif", "Noto Sans Hebrew")'

BASE_THEME: dict[str, str] = {
    "font": SANS,
    "size": "10.5pt",
    "fg": 'rgb("#222222")',
    "accent": 'rgb("#1f2937")',
    "muted": 'rgb("#6b7280")',
    "heading-font": SANS,
    "heading-color": 'rgb("#111111")',
    "h1-size": "18pt",
    "h1-weight": '"semibold"',
    "h1-color": 'rgb("#111111")',
    "h1-rule": "none",  # a stroke drawn under h1, or none
    "h2-size": "13pt",
    "h2-rule": "none",
    "h3-size": "11pt",
    "h3-style": '"normal"',
    "h3-upper": "false",
    "th-fill": "none",
    "th-fg": 'rgb("#111111")',
    "th-line": '1pt + rgb("#222222")',  # under the header row
    "row-line": "none",  # under body rows
    "band": "none",  # fill of every second body row
    "table-frame": "none",  # outer border
    "quote-line": 'rgb("#d1d5db")',
    "quote-fill": "none",
    "quote-style": '"normal"',
    "rule": 'rgb("#dddddd")',
    "link": 'rgb("#1d4ed8")',
    "leading": "0.65em",
}

THEMES: dict[str, dict[str, str]] = {
    "classic": {
        "font": SERIF, "size": "11pt", "fg": 'rgb("#1f1f1f")', "heading-font": SERIF,
        "h1-size": "22pt", "h1-weight": '"regular"', "h2-size": "16pt",
        "h2-rule": '0.8pt + rgb("#c9c2b6")', "h3-size": "13pt", "h3-style": '"italic"',
        "th-line": '1.5pt + rgb("#333333")', "row-line": '0.6pt + rgb("#ddd6ca")',
        "quote-line": 'rgb("#c9c2b6")', "quote-style": '"italic"', "rule": 'rgb("#c9c2b6")',
        "link": 'rgb("#6b3e1d")', "muted": 'rgb("#666666")',
    },
    "modern": {
        "size": "10.5pt", "fg": 'rgb("#0f172a")', "accent": 'rgb("#2563eb")',
        "muted": 'rgb("#64748b")', "h1-size": "24pt", "h1-weight": '"bold"',
        "h1-color": 'rgb("#2563eb")', "h2-size": "14pt", "h3-size": "10.5pt", "h3-upper": "true",
        "th-fill": 'rgb("#2563eb")', "th-fg": 'rgb("#ffffff")', "th-line": "none",
        "row-line": '0.6pt + rgb("#e2e8f0")', "quote-line": 'rgb("#2563eb")',
        "quote-fill": 'rgb("#eff6ff")', "rule": 'rgb("#e2e8f0")', "link": 'rgb("#2563eb")',
    },
    "minimal": {},
    "corporate": {
        "size": "10pt", "accent": 'rgb("#1e3a5f")', "h1-size": "20pt", "h1-weight": '"bold"',
        "h1-color": 'rgb("#1e3a5f")', "h1-rule": '2.2pt + rgb("#1e3a5f")', "h2-size": "13pt",
        "heading-color": 'rgb("#1e3a5f")', "th-fill": 'rgb("#1e3a5f")', "th-fg": 'rgb("#ffffff")',
        "th-line": "none", "row-line": '0.6pt + rgb("#c8d1dc")', "band": 'rgb("#f2f5f9")',
        "table-frame": '0.6pt + rgb("#c8d1dc")', "quote-line": 'rgb("#c8d1dc")',
        "quote-fill": 'rgb("#f2f5f9")', "rule": 'rgb("#1e3a5f")', "link": 'rgb("#1e3a5f")',
        "muted": 'rgb("#555555")',
    },
    "none": {"th-line": "none"},
}

PREAMBLE = r"""
#set par(leading: tp.leading, spacing: 0.9em)
#set text(font: tp.font, size: tp.size, fill: tp.fg)
#show heading: set text(font: tp.heading-font, fill: tp.heading-color)
#show heading: set block(above: 1.1em, below: 0.6em)
#show heading.where(level: 1): it => {
  set text(size: tp.h1-size, weight: tp.h1-weight, fill: tp.h1-color)
  let pad = if tp.h1-rule == none { 0pt } else { 4pt }
  block(above: 0.4em, below: 0.7em, width: 100%,
        stroke: (bottom: tp.h1-rule), inset: (bottom: pad), it.body)
}
#show heading.where(level: 2): it => {
  set text(size: tp.h2-size, weight: "bold")
  let pad = if tp.h2-rule == none { 0pt } else { 3pt }
  block(above: 1.2em, below: 0.5em, width: 100%,
        stroke: (bottom: tp.h2-rule), inset: (bottom: pad), it.body)
}
#show heading.where(level: 3): it => {
  set text(size: tp.h3-size, weight: "bold", style: tp.h3-style)
  block(above: 1em, below: 0.4em, if tp.h3-upper { upper(it.body) } else { it.body })
}
#show heading.where(level: 4): set text(size: tp.size, weight: "bold")
#show link: set text(fill: tp.link)
#set table(inset: (x: 7pt, y: 5pt))
#let tp-quote(body) = block(
  width: 100%, fill: tp.quote-fill, inset: (x: 10pt, y: 6pt),
  stroke: if tp-rtl { (right: 3pt + tp.quote-line) } else { (left: 3pt + tp.quote-line) },
  text(style: tp.quote-style, body))
#let tp-table(columns: (), header-rows: 0, ..cells) = table(
  columns: columns,
  fill: (x, y) => if y < header-rows { tp.th-fill }
    else if tp.band != none and calc.odd(y - header-rows) { tp.band } else { none },
  stroke: (x, y) => (bottom: if y < header-rows { tp.th-line } else { tp.row-line }),
  ..cells)
#let tp-th(body) = text(fill: tp.th-fg, weight: "bold", body)
#let tp-hr() = line(length: 100%, stroke: 0.6pt + tp.rule)
"""

# ---------------------------------------------------------------------------
# Value helpers (everything emitted as code is validated here)
# ---------------------------------------------------------------------------

_HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
_RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")
_LEN = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(px|pt|mm|cm|in|em|rem)?\s*$")
_LANG = re.compile(r"^[a-z]{2,3}$")
_RTL_CHARS = re.compile("[֐-ࣿיִ-﷿ﹰ-ﻼ]")
PAPERS = {"A3": "a3", "A4": "a4", "A5": "a5", "Letter": "us-letter", "Legal": "us-legal"}


def tstr(text: str) -> str:
    """A Typst string literal (the only way document text enters the source)."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def tcolor(css: str | None) -> str | None:
    if not css:
        return None
    m = _HEX.search(css)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return f'rgb("#{h.lower()}")'
    m = _RGB.search(css)
    if m:
        r, g, b = (min(255, int(x)) for x in m.groups())
        return f"rgb({r}, {g}, {b})"
    return None


def tlength(css: str | None, *, default_unit: str = "px") -> str | None:
    if not css:
        return None
    m = _LEN.match(css)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2) or default_unit
    if unit == "px":
        return f"{n * 0.75:.2f}pt"
    if unit == "rem":
        unit = "em"
    return f"{n:g}{unit}"


def margins(page: PageSettings) -> str:
    parts = [tlength(p, default_unit="mm") or "20mm" for p in (page.margin or "20mm").split()]
    if len(parts) == 1:
        parts *= 4
    elif len(parts) == 2:
        parts = [parts[0], parts[1], parts[0], parts[1]]
    elif len(parts) == 3:
        parts = [parts[0], parts[1], parts[2], parts[1]]
    top, right, bottom, left = parts[:4]
    return f"(top: {top}, right: {right}, bottom: {bottom}, left: {left})"


def is_rtl_text(text: str) -> bool:
    return bool(_RTL_CHARS.search(text or ""))


def first_strong(text: str) -> str | None:
    """Direction of the first letter ("rtl"/"ltr"), or None for digits/punctuation only.

    Paragraphs take their direction from it, like CSS ``unicode-bidi: plaintext``:
    an English line in a Hebrew document stays left-to-right, and vice versa.
    """
    for ch in text or "":
        if _RTL_CHARS.match(ch):
            return "rtl"
        if ch.isalpha():
            return "ltr"
    return None


# ---------------------------------------------------------------------------
# HTML -> Typst
# ---------------------------------------------------------------------------

_BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "blockquote",
    "pre", "hr", "main", "header", "footer", "section", "article", "thead", "tbody", "tr",
}  # fmt: skip


class TypstWriter:
    def __init__(self, load_image, workdir: Path, direction: str = "ltr"):
        self.load_image = load_image  # (src) -> bytes | None
        self.workdir = workdir
        self.direction = direction
        self.images = 0

    def directed(self, text: str, body: str) -> str:
        """Give a paragraph the direction of its first letter when it differs from the document's."""
        own = first_strong(text)
        if own and own != self.direction:
            return f"#text(dir: {own})[{body}]"
        return body

    # -- inline --------------------------------------------------------------
    def inline(self, nodes, preserve_ws: bool = False) -> str:
        out = []
        for node in nodes:
            if isinstance(node, str):
                text = node if preserve_ws else re.sub(r"\s+", " ", node)
                if text:
                    out.append("#" + tstr(text))
                continue
            out.append(self.inline_el(node, preserve_ws))
        return "".join(out)

    def inline_el(self, el: El, preserve_ws: bool) -> str:
        tag = el.tag
        classes = el.classes()
        if "tp-page-number" in classes:
            return "#context counter(page).display()"
        if "tp-page-count" in classes:
            return "#context counter(page).final().first()"
        if tag == "br":
            return "#linebreak()"
        if tag == "img":
            return self.image(el)
        if tag == "code":
            return "#text(dir: ltr)[#raw(" + tstr(_text_of(el)) + ")]"
        if tag in _BLOCK_TAGS:  # a block inside inline content: flatten
            return self.inline(el.children, preserve_ws) + "#linebreak()"
        body = self.inline(el.children, preserve_ws)
        if not body:
            return ""
        wrap = []
        if tag in ("strong", "b"):
            wrap.append("strong")
        elif tag in ("em", "i"):
            wrap.append("emph")
        elif tag == "u":
            wrap.append("underline")
        elif tag in ("s", "del"):
            wrap.append("strike")
        elif tag == "sub":
            wrap.append("sub")
        elif tag == "sup":
            wrap.append("super")
        elif tag == "small":
            wrap.append("text(size: 0.85em)")
        elif tag == "mark":
            mark_fill = tcolor(el.style().get("background-color")) or 'rgb("#fde68a")'
            wrap.append(f"highlight(fill: {mark_fill})")
        elif tag == "a":
            href = el.attrs.get("href") or ""
            if href:
                wrap.append(f"link({tstr(href)})")
        st = el.style()
        args = []
        color = tcolor(st.get("color"))
        if color:
            args.append(f"fill: {color}")
        size = tlength(st.get("font-size"))
        if size:
            args.append(f"size: {size}")
        if st.get("font-weight") in ("bold", "600", "700", "800", "900"):
            args.append('weight: "bold"')
        if st.get("font-style") == "italic":
            args.append('style: "italic"')
        if args:
            wrap.append("text(" + ", ".join(args) + ")")
        bg = tcolor(st.get("background-color"))
        if bg and tag != "mark":
            wrap.append(f"highlight(fill: {bg})")
        deco = st.get("text-decoration", "")
        if "underline" in deco and tag != "u":
            wrap.append("underline")
        if "line-through" in deco and tag not in ("s", "del"):
            wrap.append("strike")
        for fn in reversed(wrap):
            body = f"#{fn}[{body}]"
        return body

    def image(self, el: El) -> str:
        data = self.load_image(el.attrs.get("src", ""))
        ext = _image_ext(data) if data else None
        alt = el.attrs.get("alt") or ""
        if not ext:
            return "#" + tstr(f"[{alt}]") if alt else ""
        self.images += 1
        name = f"img{self.images}.{ext}"
        (self.workdir / name).write_bytes(data)
        width = tlength(el.attrs.get("width") or el.style().get("width"))
        size = f", width: {width}" if width else ""
        return f'#box(image("{name}"{size}))'

    # -- blocks --------------------------------------------------------------
    def blocks(self, nodes) -> str:
        out: list[str] = []
        pending: list = []

        def flush():
            items = _trim(pending)
            if items:
                text = self.inline(items)
                if text:
                    out.append(self.directed("".join(_text_of(i) for i in items), text))
            pending.clear()

        for node in nodes:
            if isinstance(node, El) and node.tag in _BLOCK_TAGS:
                flush()
                rendered = self.block(node)
                if rendered:
                    out.append(rendered)
            else:
                pending.append(node)
        flush()
        return "\n\n".join(out)

    def aligned(self, el: El, body: str) -> str:
        align = el.style().get("text-align")
        if align in ("center", "left", "right"):
            return f"#align({align})[{body}]"
        if align == "justify":
            return f"#par(justify: true)[{body}]"
        return body

    def block(self, el: El) -> str:
        tag = el.tag
        if tag == "p":
            body = self.inline(_trim(el.children))
            if not body:
                return "#v(0.5em)"
            return self.aligned(el, self.directed(_text_of(el), body))
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = min(int(tag[1]), 4)
            body = self.inline(_trim(el.children))
            if not body:
                return ""
            return self.aligned(el, self.directed(_text_of(el), f"#heading(level: {level})[{body}]"))
        if tag in ("ul", "ol"):
            items = [c for c in el.children if isinstance(c, El) and c.tag == "li"]
            if not items:
                return ""
            parts = ", ".join(f"[{self.blocks(li.children)}]" for li in items)
            if tag == "ol":
                start = el.attrs.get("start")
                start_arg = f"start: {int(start)}, " if start and start.isdigit() else ""
                return f"#enum({start_arg}{parts})"
            return f"#list({parts})"
        if tag == "li":
            return self.blocks(el.children)
        if tag == "blockquote":
            return f"#tp-quote[{self.blocks(el.children)}]"
        if tag == "pre":
            return "#text(dir: ltr)[#raw(" + tstr(_text_of(el)) + ", block: true)]"
        if tag == "hr":
            return "#tp-hr()"
        if tag == "table":
            return self.table(el)
        return self.blocks(el.children)

    def table(self, el: El) -> str:
        rows: list[El] = []

        def collect(node: El):
            for c in node.children:
                if isinstance(c, El):
                    if c.tag == "tr":
                        rows.append(c)
                    elif c.tag in ("thead", "tbody", "tfoot"):
                        collect(c)

        collect(el)
        grid = [[c for c in r.children if isinstance(c, El) and c.tag in ("td", "th")] for r in rows]
        grid = [r for r in grid if r]
        if not grid:
            return ""
        ncols = max(sum(_span(c, "colspan") for c in r) for r in grid)
        header_rows = 0
        for r in grid:
            if all(c.tag == "th" for c in r):
                header_rows += 1
            else:
                break
        if header_rows == len(grid):  # a table of only <th> rows is not a header
            header_rows = 0
        # Column weights from content length (single-span cells only).
        lengths = [1] * ncols
        for r in grid:
            col = 0
            for c in r:
                span = _span(c, "colspan")
                if span == 1 and col < ncols:
                    lengths[col] = max(lengths[col], len(_text_of(c)))
                col += span
        weights = [max(1, min(8, round(math.sqrt(n)))) for n in lengths]
        columns = "(" + ", ".join(f"{w}fr" for w in weights) + ("," if ncols == 1 else "") + ")"

        def cell(c: El, in_header: bool) -> str:
            body = self.blocks(c.children)
            if c.tag == "th":
                body = f"#tp-th[{body}]" if in_header else f"#strong[{body}]"
            args = []
            cs, rs = _span(c, "colspan"), _span(c, "rowspan")
            if cs > 1:
                args.append(f"colspan: {cs}")
            if rs > 1:
                args.append(f"rowspan: {rs}")
            fill = tcolor(c.style().get("background-color"))
            if fill:
                args.append(f"fill: {fill}")
            align = c.style().get("text-align")
            if align in ("left", "right", "center"):
                args.append(f"align: {align}")
            return (f"table.cell({', '.join(args)})" if args else "") + f"[{body}]"

        parts = []
        if header_rows:
            head = ", ".join(cell(c, True) for r in grid[:header_rows] for c in r)
            parts.append(f"table.header({head})")
        for r in grid[header_rows:]:
            parts.extend(cell(c, False) for c in r)
        return f"#tp-table(columns: {columns}, header-rows: {header_rows}, " + ", ".join(parts) + ")"


def _span(el: El, attr: str) -> int:
    try:
        return max(1, min(50, int(el.attrs.get(attr) or 1)))
    except ValueError:
        return 1


def _text_of(el) -> str:
    if isinstance(el, str):
        return el
    return "".join(_text_of(c) for c in el.children)


def _trim(nodes: list) -> list:
    """Drop leading/trailing whitespace of a run of inline nodes (HTML collapsing)."""
    items = list(nodes)
    while items and isinstance(items[0], str) and not items[0].strip():
        items.pop(0)
    while items and isinstance(items[-1], str) and not items[-1].strip():
        items.pop()
    if items and isinstance(items[0], str):
        items[0] = items[0].lstrip()
    if items and isinstance(items[-1], str):
        items[-1] = items[-1].rstrip()
    return items


def _image_ext(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG"):
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    head = data[:300].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2000]):
        return "svg"
    return None


def theme_block(theme: dict[str, str] | None) -> str:
    values = {**BASE_THEME, **(theme or {})}
    pairs = ",\n  ".join(f"{k}: {v}" for k, v in values.items())
    return f"#let tp = (\n  {pairs},\n)"


class TypstPdfRenderer(Renderer):
    name = "pdf"
    mimetype = "application/pdf"
    extension = "pdf"
    label = "PDF"
    engine = "typst"

    def __init__(self, *, font_paths: list[str] | None = None, ignore_system_fonts: bool = False,
                 themes: dict[str, dict[str, str]] | None = None):
        self.font_paths = [str(FONTS_DIR), *(font_paths or [])]
        self.ignore_system_fonts = ignore_system_fonts
        self.themes = {**THEMES, **(themes or {})}

    def is_available(self) -> bool:
        try:
            import typst  # noqa: F401
        except ImportError:
            return False
        return True

    def build_source(self, doc: RenderInput, workdir: Path) -> str:
        rtl = doc.direction == "rtl"
        writer = TypstWriter(lambda src: self.load_image(src, doc), workdir,
                             direction="rtl" if rtl else "ltr")
        lang = doc.lang if _LANG.match(doc.lang or "") else "en"
        paper = PAPERS.get(doc.page.size, "a4")
        flipped = "true" if doc.page.orientation == "landscape" else "false"
        page_args = [f'paper: "{paper}"', f"flipped: {flipped}", f"margin: {margins(doc.page)}"]
        if doc.header_html:
            header = writer.blocks(parse_html(doc.header_html).children)
            page_args.append(f"header: text(size: 0.85em, fill: tp.muted)[{header}]")
        if doc.footer_html:
            footer = writer.blocks(parse_html(doc.footer_html).children)
            page_args.append(f"footer: text(size: 0.85em, fill: tp.muted)[{footer}]")
        body = writer.blocks(parse_html(doc.body_html).children)
        theme = self.themes.get(doc.theme or "", self.themes.get("minimal"))
        return "\n".join([
            theme_block(theme),
            f"#let tp-rtl = {'true' if rtl else 'false'}",
            PREAMBLE,
            f"#set document(title: {tstr(doc.title or 'Document')})",
            f'#set text(lang: "{lang}", dir: {"rtl" if rtl else "ltr"})',
            "#set page(" + ", ".join(page_args) + ")",
            "",
            body,
            "",
        ])

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
            data = res.get("string")
            if data is None and res.get("file_obj") is not None:
                data = res["file_obj"].read()
            if isinstance(data, str):
                data = data.encode()
            return data
        return None

    def render(self, doc: RenderInput) -> bytes:
        try:
            import typst
        except ImportError as exc:
            raise RendererUnavailable("PDF output needs the 'typst' package: pip install typst") from exc
        with tempfile.TemporaryDirectory(prefix="tp-typst-") as tmp:
            workdir = Path(tmp)
            source = self.build_source(doc, workdir)
            main = workdir / "main.typ"
            main.write_text(source, encoding="utf-8")
            try:
                return typst.compile(str(main), root=str(workdir), font_paths=self.font_paths,
                                     ignore_system_fonts=self.ignore_system_fonts, format="pdf")
            except Exception as exc:  # TypstError: report, don't leak a traceback
                raise RuntimeError(f"Typst could not build the PDF: {exc}") from exc
