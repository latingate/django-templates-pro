"""A small Markdown-to-HTML converter for the demo's documentation pages.

It covers what this repository's ``.md`` files use: headings (with GitHub-style
anchors), paragraphs, fenced code, lists (nested, with paragraphs and code
inside items), tables, block quotes, rules, and inline code, links, bold and
italic. All text is HTML-escaped; raw HTML in the source is shown as text.

It exists so that the demo needs no extra dependency. It is not a general
Markdown implementation.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)\s*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+)(.*)$")
_RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")

_CODE_SPAN = re.compile(r"(`+)(.+?)\1", re.S)
_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+&quot;[^)]*&quot;)?\)")
_AUTOLINK = re.compile(r"&lt;(https?://[^\s&]+)&gt;")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.S)
_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", re.S)
_ITALIC_UNDER = re.compile(r"(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])", re.S)

LinkResolver = Callable[[str], "str | None"]


def slugify(text: str) -> str:
    """GitHub's heading anchor: lower case, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text.strip().lower())
    return text.replace(" ", "-")


class Markdown:
    def __init__(self, resolve_link: LinkResolver | None = None):
        self.resolve_link = resolve_link
        self.toc: list[tuple[int, str, str]] = []  # (level, anchor, plain title)
        self._anchors: dict[str, int] = {}

    # -- inline ---------------------------------------------------------------
    def inline(self, text: str) -> str:
        spans: list[str] = []

        def stash(match):
            spans.append(f"<code>{html.escape(match.group(2).strip(), quote=False)}</code>")
            return f"\x00{len(spans) - 1}\x00"

        text = _CODE_SPAN.sub(stash, text)
        text = html.escape(text, quote=True)
        text = _LINK.sub(self._link, text)
        text = _AUTOLINK.sub(r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)
        text = _BOLD.sub(r"<strong>\1</strong>", text)
        text = _ITALIC_STAR.sub(r"<em>\1</em>", text)
        text = _ITALIC_UNDER.sub(r"<em>\1</em>", text)
        return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)

    def _link(self, match) -> str:
        image, label, target = match.group(1), match.group(2), html.unescape(match.group(3))
        if image:
            return label
        href = self.resolve_link(target) if self.resolve_link else target
        if href is None:
            return label  # a file this viewer does not serve
        external = re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) is not None
        if external and not re.match(r"^(https?|mailto):", href, re.I):
            return label
        extra = ' target="_blank" rel="noopener noreferrer"' if external else ""
        return f'<a href="{html.escape(href, quote=True)}"{extra}>{label}</a>'

    # -- blocks ---------------------------------------------------------------
    def convert(self, source: str) -> str:
        lines = source.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n")
        return self.blocks(lines)

    def blocks(self, lines: list[str]) -> str:
        out: list[str] = []
        i, n = 0, len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue
            fence = _FENCE.match(line)
            if fence:
                i = self._fence(lines, i, fence, out)
            elif _HEADING.match(line):
                self._heading(_HEADING.match(line), out)
                i += 1
            elif _RULE.match(line):
                out.append("<hr>")
                i += 1
            elif _QUOTE.match(line):
                i = self._quote(lines, i, out)
            elif _ITEM.match(line):
                i = self._list(lines, i, out)
            elif "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
                i = self._table(lines, i, out)
            else:
                i = self._paragraph(lines, i, out)
        return "\n".join(out)

    def _starts_block(self, line: str) -> bool:
        return bool(_FENCE.match(line) or _HEADING.match(line) or _RULE.match(line)
                    or _QUOTE.match(line) or _ITEM.match(line))

    def _fence(self, lines, i, fence, out) -> int:
        indent, marker, lang = len(fence.group(1)), fence.group(2), fence.group(3)
        body = []
        i += 1
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith(marker[0] * len(marker)) and not stripped.strip(marker[0]):
                i += 1
                break
            body.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i].lstrip())
            i += 1
        cls = f' class="language-{html.escape(lang)}"' if lang else ""
        out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body), quote=False)}</code></pre>")
        return i

    def _heading(self, match, out) -> None:
        level, raw = len(match.group(1)), match.group(2)
        base = slugify(raw) or "section"
        count = self._anchors.get(base, 0)
        self._anchors[base] = count + 1
        anchor = base if not count else f"{base}-{count}"
        rendered = self.inline(raw)
        self.toc.append((level, anchor, re.sub(r"<[^>]+>", "", rendered)))
        out.append(f'<h{level} id="{html.escape(anchor, quote=True)}">{rendered}</h{level}>')

    def _quote(self, lines, i, out) -> int:
        body = []
        while i < len(lines):
            match = _QUOTE.match(lines[i])
            if match:
                body.append(match.group(1))
            elif lines[i].strip() and body and body[-1].strip() and not self._starts_block(lines[i]):
                body.append(lines[i])  # lazy continuation
            else:
                break
            i += 1
        out.append(f"<blockquote>{self.blocks(body)}</blockquote>")
        return i

    def _paragraph(self, lines, i, out) -> int:
        body = [lines[i].strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not self._starts_block(lines[i]):
            body.append(lines[i].strip())
            i += 1
        out.append(f"<p>{self.inline(' '.join(body))}</p>")
        return i

    def _list(self, lines, i, out) -> int:
        first = _ITEM.match(lines[i])
        base = len(first.group(1))
        ordered = first.group(2)[0].isdigit()
        items: list[list[str]] = []
        loose = False
        while i < len(lines):
            match = _ITEM.match(lines[i])
            if not match or len(match.group(1)) != base or match.group(2)[0].isdigit() != ordered:
                break
            content = base + len(match.group(2)) + len(match.group(3))
            body = [match.group(4)]
            i += 1
            while i < len(lines):
                line = lines[i]
                if not line.strip():
                    # A blank line stays in the item only when indented content follows it.
                    j = i
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and len(lines[j]) - len(lines[j].lstrip()) > base:
                        body.extend([""] * (j - i))
                        i = j
                        continue
                    break
                indent = len(line) - len(line.lstrip())
                if indent > base:
                    body.append(line[min(indent, content):])
                elif body[-1].strip() and not self._starts_block(line):
                    body.append(line.strip())  # lazy continuation of the item's paragraph
                else:
                    break
                i += 1
            if "" in body:
                loose = True
            items.append(body)
            # Blank lines between items of the same list.
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            nxt = _ITEM.match(lines[j]) if j < len(lines) else None
            if nxt and len(nxt.group(1)) == base and nxt.group(2)[0].isdigit() == ordered:
                i = j
        tag = "ol" if ordered else "ul"
        start = first.group(2)[:-1]
        attr = f' start="{start}"' if ordered and start != "1" else ""
        out.append(f"<{tag}{attr}>")
        for body in items:
            rendered = self.blocks(body)
            if not loose and rendered.startswith("<p>"):
                rendered = rendered.replace("<p>", "", 1).replace("</p>", "", 1)
            out.append(f"<li>{rendered}</li>")
        out.append(f"</{tag}>")
        return i

    @staticmethod
    def _cells(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        cells, cell, in_code, k = [], [], False, 0
        while k < len(line):
            ch = line[k]
            if ch == "\\" and k + 1 < len(line) and line[k + 1] == "|":
                cell.append("|")
                k += 2
                continue
            if ch == "`":
                in_code = not in_code
            if ch == "|" and not in_code:
                cells.append("".join(cell).strip())
                cell = []
            else:
                cell.append(ch)
            k += 1
        if "".join(cell).strip():
            cells.append("".join(cell).strip())
        return cells

    def _table(self, lines, i, out) -> int:
        head = self._cells(lines[i])
        aligns = []
        for spec in self._cells(lines[i + 1]):
            left, right = spec.startswith(":"), spec.endswith(":")
            aligns.append("center" if left and right else "right" if right else "")
        i += 2
        rows = []
        while i < len(lines) and lines[i].strip() and "|" in lines[i]:
            rows.append(self._cells(lines[i]))
            i += 1

        def row(cells, tag):
            parts = []
            for k in range(len(head)):
                text = cells[k] if k < len(cells) else ""
                align = aligns[k] if k < len(aligns) else ""
                style = f' style="text-align:{align}"' if align else ""
                parts.append(f"<{tag}{style}>{self.inline(text)}</{tag}>")
            return "<tr>" + "".join(parts) + "</tr>"

        body = "".join(row(r, "td") for r in rows)
        out.append(f'<div class="table-wrap"><table><thead>{row(head, "th")}</thead>'
                   f"<tbody>{body}</tbody></table></div>")
        return i
