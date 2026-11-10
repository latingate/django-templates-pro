"""Compile editor HTML into sandboxed Jinja2 source (and sanitize it).

The editor never stores template syntax. It stores HTML in which dynamic parts
are *chips* identified by ``data-tp`` attributes. This module is the single
place where that HTML contract is defined::

    <span data-tp="var" data-path="invoice.total" data-format='{"kind":"money"}'>Total</span>
    <span data-tp="const" data-key="site_name">Site name</span>
    <span data-tp="dynamic" data-key="today" data-format='{"kind":"date","style":"long"}'>Today</span>
    <div  data-tp="block" data-slug="company-header"></div>
    <div  data-tp="repeat" data-path="invoice.lines" data-as="line"> ... </div>
    <div  data-tp="if" data-path="invoice.discount" data-op="gt" data-value="0"> ... </div>
    <tr   data-tp-repeat="invoice.lines" data-tp-as="line"> ... </tr>

Everything else is ordinary rich-text HTML, filtered through a tag/attribute/
style allowlist. Literal text is entity-encoded so that ``{{ }}`` typed by a
user is never executed. User input never reaches Jinja syntax unescaped:
paths and keys are validated identifiers and format specs become escaped
string literals that are parsed as JSON at render time.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from . import schema as sch
from .formatting import CONDITION_OPS, DATE_STYLES, FORMAT_KINDS

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "ins", "sub", "sup", "mark", "small",
    "span", "div", "a", "img", "code", "pre", "blockquote",
    "ul", "ol", "li",
    "table", "colgroup", "col", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
}  # fmt: skip
VOID_TAGS = {"br", "hr", "img", "col", "wbr"}
#: Tags removed together with their content.
DROP_CONTENT_TAGS = {
    "script", "style", "iframe", "object", "embed", "template", "noscript",
    "svg", "math", "form", "input", "button", "select", "textarea", "head", "title",
}  # fmt: skip

GLOBAL_ATTRS = {"style", "class", "dir"}
TAG_ATTRS = {
    "a": {"href", "target", "rel", "title"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan", "colwidth"},
    "th": {"colspan", "rowspan", "colwidth", "scope"},
    "col": {"span", "width"},
    "ol": {"start", "type"},
}

ALLOWED_STYLE_PROPS = {
    "text-align", "vertical-align", "color", "background-color",
    "font-size", "font-family", "font-weight", "font-style", "line-height", "letter-spacing",
    "text-decoration", "text-transform", "white-space",
    "width", "min-width", "max-width", "height",
    "border", "border-top", "border-right", "border-bottom", "border-left",
    "border-color", "border-width", "border-style", "border-collapse", "border-radius",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "float", "page-break-before", "page-break-after", "break-before", "break-after",
}  # fmt: skip
_STYLE_VALUE_RE = re.compile(r"^[#%(),.\-\w\s'\"/]+$")
_STYLE_BAD = ("url(", "expression", "javascript:", "@import", "\\", "/*", "<", ">")
_CLASS_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,99}$")
_IMG_DATA_RE = re.compile(r"^data:image/(png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=\s]+$", re.I)

DYNAMIC_VALUES: dict[str, dict[str, Any]] = {
    "now": {"label": "Current date & time", "type": "datetime"},
    "today": {"label": "Today's date", "type": "date"},
    "time": {"label": "Current time", "type": "time"},
    "year": {"label": "Current year", "type": "integer"},
    "row_number": {"label": "Row number (inside a repeat)", "type": "integer"},
    "page_number": {"label": "Page number (PDF)", "type": "integer"},
    "page_count": {"label": "Page count (PDF)", "type": "integer"},
}

#: Hard cap on chip nesting / loops handled at render time (see engine).
MAX_NESTING = 20


class TemplateCompileError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class CompileResult:
    source: str
    #: Recorded variable paths, loop items as ``invoice.lines[].qty``.
    variables: set[str] = field(default_factory=set)
    constants: set[str] = field(default_factory=set)
    blocks: set[str] = field(default_factory=set)
    dynamic: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_for_errors(self) -> CompileResult:
        if self.errors:
            raise TemplateCompileError(self.errors)
        return self


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def jinja_string_literal(text: str) -> str:
    """Return a Jinja string literal that is safe inside ``{{ }}`` / ``{% %}``.

    Braces, ``%`` and ``#`` are \\u-escaped so the lexer can never see a block
    delimiter inside the literal; Jinja decodes the escapes back.
    """
    lit = json.dumps(text, ensure_ascii=True)
    for ch, esc in (("{", "\\u007b"), ("}", "\\u007d"), ("%", "\\u0025"), ("#", "\\u0023")):
        lit = lit.replace(ch, esc)
    return lit


def _escape_text(text: str) -> str:
    return html.escape(text, quote=False).replace("{", "&#123;").replace("}", "&#125;")


def _escape_attr(value: str) -> str:
    return html.escape(value, quote=True).replace("{", "&#123;").replace("}", "&#125;")


def path_expr(path: str) -> str:
    head, *rest = path.split(".")
    return head + "".join(f'["{part}"]' for part in rest)


def clean_style(style: str) -> str:
    out = []
    for decl in style.split(";"):
        if ":" not in decl:
            continue
        prop, value = decl.split(":", 1)
        prop, value = prop.strip().lower(), value.strip()
        low = value.lower()
        if (
            prop in ALLOWED_STYLE_PROPS
            and value
            and len(value) < 200
            and _STYLE_VALUE_RE.match(value)
            and not any(bad in low for bad in _STYLE_BAD)
        ):
            out.append(f"{prop}: {value}")
    return "; ".join(out)


def clean_url(url: str, *, image: bool = False) -> str | None:
    url = (url or "").strip()
    low = re.sub(r"[\x00-\x20]", "", url.lower())
    if image and low.startswith("data:"):
        return url if _IMG_DATA_RE.match(url) else None
    if low.startswith(("http://", "https://")):
        return url
    if not image and low.startswith(("mailto:", "tel:", "#")):
        return url
    if low.startswith("/") and not low.startswith("//"):
        return url
    return None


def parse_format(raw: str | None) -> tuple[dict, str | None]:
    """Parse and validate a ``data-format`` JSON spec. Returns (spec, error)."""
    if not raw:
        return {}, None
    try:
        spec = json.loads(raw)
    except ValueError:
        return {}, "invalid format settings (not JSON)"
    if not isinstance(spec, dict):
        return {}, "invalid format settings"
    clean: dict[str, Any] = {}
    for key, value in spec.items():
        if not isinstance(key, str) or len(key) > 30:
            return {}, "invalid format key"
        if value is None:
            continue
        if not isinstance(value, (str, int, float, bool)) or (
            isinstance(value, str) and len(value) > 200
        ):
            return {}, f"invalid format value for {key!r}"
        clean[key] = value
    kind = clean.get("kind", "auto")
    if kind not in FORMAT_KINDS:
        return {}, f"unknown format kind {kind!r}"
    if "style" in clean and clean["style"] not in DATE_STYLES:
        return {}, f"unknown date style {clean['style']!r}"
    return clean, None


# ---------------------------------------------------------------------------
# The compiler
# ---------------------------------------------------------------------------


@dataclass
class _Scope:
    alias: str
    flat_path: str  # e.g. "invoice.lines[]"
    item: dict | None  # item fields when the schema is known


class _Compiler(HTMLParser):
    def __init__(
        self,
        *,
        mode: str,
        schema: dict | None,
        constants: set[str] | None,
        blocks: set[str] | None,
    ):
        super().__init__(convert_charrefs=True)
        self.mode = mode  # "jinja" | "clean"
        self.schema = schema
        self.known_constants = constants
        self.known_blocks = blocks
        self.out: list[str] = []
        self.stack: list[tuple[str, str, bool]] = []  # (tag, closer, pushed_scope)
        self.scopes: list[_Scope] = []
        self.skip_tag: str | None = None
        self.skip_depth = 0
        self.pending_chip: tuple[str, dict, dict, str] | None = None
        self.chip_text: list[str] = []
        self.result = CompileResult(source="")

    # -- utilities ---------------------------------------------------------
    def err(self, msg: str):
        if msg not in self.result.errors:
            self.result.errors.append(msg)

    def warn(self, msg: str):
        if msg not in self.result.warnings:
            self.result.warnings.append(msg)

    def start_skip(self, tag: str):
        self.skip_tag, self.skip_depth = tag, 1

    def scope_map(self) -> dict[str, dict]:
        return {s.alias: (s.item or {}) for s in self.scopes}

    def record_path(self, path: str) -> tuple[str, sch.Node | None, bool]:
        """Return (flat_path, schema_node, known)."""
        head, *rest = path.split(".")
        for scope in reversed(self.scopes):
            if scope.alias == head:
                flat = ".".join([scope.flat_path, *rest]) if rest else scope.flat_path
                node = None
                if scope.item is not None:
                    node = sch.resolve({}, path, {head: scope.item}) if rest else None
                return flat, node, scope.item is None or node is not None
        node = sch.resolve(self.schema, path) if self.schema is not None else None
        return path, node, self.schema is None or node is not None

    def attrs_dict(self, attrs) -> dict[str, str]:
        return {k.lower(): (v if v is not None else "") for k, v in attrs}

    def emit_tag(self, tag: str, attrs: dict[str, str], *, keep_tp: dict | None = None) -> str:
        parts = [tag]
        allowed = GLOBAL_ATTRS | TAG_ATTRS.get(tag, set())
        for name, value in attrs.items():
            if name not in allowed:
                continue
            if name == "style":
                value = clean_style(value)
                if not value:
                    continue
            elif name == "class":
                if not _CLASS_RE.match(value):
                    continue
            elif name == "href":
                value = clean_url(value)
                if value is None:
                    continue
            elif name == "src":
                value = clean_url(value, image=True)
                if value is None:
                    continue
            elif name == "target":
                if value != "_blank":
                    continue
            elif name in ("colspan", "rowspan", "span", "start", "width", "height", "colwidth"):
                if not re.match(r"^[0-9,]{1,10}$", value):
                    continue
            parts.append(f'{name}="{_escape_attr(value)}"')
        if tag == "a" and attrs.get("target") == "_blank":
            parts = [p for p in parts if not p.startswith("rel=")]
            parts.append('rel="noopener noreferrer"')
        for name, value in (keep_tp or {}).items():
            if value is not None and value != "":
                parts.append(f'{name}="{_escape_attr(value)}"')
        return "<" + " ".join(parts) + ">"

    # -- chips ---------------------------------------------------------------
    def chip_inline(self, tag: str, a: dict[str, str]) -> None:
        kind = a.get("data-tp")
        spec, ferr = parse_format(a.get("data-format"))
        label = a.get("data-label", "")
        if ferr:
            self.err(f"{kind} chip: {ferr}")
            return
        if kind == "var":
            path = a.get("data-path", "")
            if not sch.PATH_RE.match(path):
                self.err(f"variable chip has an invalid path {path!r}")
                return
            flat, node, known = self.record_path(path)
            self.result.variables.add(flat)
            if not known:
                self.err(f"unknown variable {path!r}")
            elif isinstance(node, (sch.Group, sch.ListOf)):
                self.err(f"{path!r} is a group or list, not a single value")
            if not spec and isinstance(node, sch.Var):
                spec = node.format or sch.default_format(node.type)
            expr = path_expr(path)
            if self.mode == "clean":
                self.out.append(self._chip_html(tag, {"data-tp": "var", "data-path": path},
                                                spec, label or path))
            else:
                self.out.append(f"{{{{ tp_format({expr}, {jinja_string_literal(json.dumps(spec))}) }}}}")
        elif kind == "const":
            key = a.get("data-key", "")
            if not sch.IDENT_RE.match(key):
                self.err(f"constant chip has an invalid key {key!r}")
                return
            self.result.constants.add(key)
            if self.known_constants is not None and key not in self.known_constants:
                self.warn(f"constant {key!r} is not defined (it will render empty)")
            if self.mode == "clean":
                self.out.append(self._chip_html(tag, {"data-tp": "const", "data-key": key},
                                                spec, label or key))
            else:
                self.out.append(
                    f'{{{{ tp_format(const["{key}"], {jinja_string_literal(json.dumps(spec))}) }}}}'
                )
        elif kind == "dynamic":
            key = a.get("data-key", "")
            if key not in DYNAMIC_VALUES:
                self.err(f"unknown dynamic value {key!r}")
                return
            self.result.dynamic.add(key)
            if key == "row_number" and not self.scopes:
                self.err("'Row number' can only be used inside a repeat section or repeated row")
            if self.mode == "clean":
                self.out.append(self._chip_html(tag, {"data-tp": "dynamic", "data-key": key},
                                                spec, label or key))
                return
            if key == "page_number":
                self.out.append('<span class="tp-page-number"></span>')
            elif key == "page_count":
                self.out.append('<span class="tp-page-count"></span>')
            else:
                expr = "loop.index" if key == "row_number" else f"tp_{key}"
                if not spec:
                    spec = sch.default_format(DYNAMIC_VALUES[key]["type"])
                if key == "year" and spec.get("kind") == "number":
                    spec = {**spec, "kind": "text"}
                self.out.append(f"{{{{ tp_format({expr}, {jinja_string_literal(json.dumps(spec))}) }}}}")
        else:
            self.err(f"unknown chip type {kind!r}")

    def _chip_html(self, tag: str, base: dict, spec: dict, label: str) -> str:
        # Clean mode: remember the chip and emit it once its label text is read.
        self.pending_chip = (tag, base, spec, label)
        self.chip_text = []
        return ""

    def _flush_chip(self) -> None:
        if not self.pending_chip:
            return
        _, base, spec, fallback = self.pending_chip
        label = "".join(self.chip_text).strip() or fallback
        self.pending_chip = None
        attrs = dict(base)
        if spec:
            attrs["data-format"] = json.dumps(spec, separators=(",", ":"))
        inner = "".join(f' {k}="{_escape_attr(v)}"' for k, v in attrs.items())
        self.out.append(f"<span{inner}>{_escape_text(label[:200])}</span>")

    def open_repeat(self, path: str, alias: str, *, row_attrs: dict | None, tag: str) -> bool:
        if not sch.PATH_RE.match(path):
            self.err(f"repeat has an invalid list path {path!r}")
            return False
        if not sch.IDENT_RE.match(alias) or alias in sch.RESERVED_NAMES or alias.startswith(
            sch.RESERVED_PREFIX
        ):
            self.err(f"invalid repeat item name {alias!r}")
            return False
        if self.schema is not None and alias in self.schema:
            self.err(f"repeat item name {alias!r} clashes with a variable group")
            return False
        if len(self.scopes) >= MAX_NESTING:
            self.err("repeat sections are nested too deeply")
            return False
        flat, node, known = self.record_path(path)
        if not known:
            self.err(f"unknown list {path!r}")
        elif node is not None and not isinstance(node, sch.ListOf):
            self.err(f"{path!r} is not a list")
        item = node.item if isinstance(node, sch.ListOf) else (
            None if (self.schema is None or not known) else {}
        )
        self.result.variables.add(flat + "[]")
        self.scopes.append(_Scope(alias=alias, flat_path=flat + "[]", item=item))
        loop = f"{{% for {alias} in tp_iter({path_expr(path)}) %}}"
        if tag == "tr":
            if self.mode == "clean":
                self.out.append(self.emit_tag("tr", row_attrs or {},
                                              keep_tp={"data-tp-repeat": path, "data-tp-as": alias}))
                self.stack.append(("tr", "</tr>", True))
            else:
                self.out.append(loop + self.emit_tag("tr", row_attrs or {}))
                self.stack.append(("tr", "</tr>{% endfor %}", True))
        else:
            if self.mode == "clean":
                self.out.append(f'<div data-tp="repeat" data-path="{_escape_attr(path)}" '
                                f'data-as="{_escape_attr(alias)}">')
                self.stack.append((tag, f"</{tag}>", True))
            else:
                self.out.append(loop)
                self.stack.append((tag, "{% endfor %}", True))
        return True

    def open_if(self, tag: str, a: dict[str, str]) -> bool:
        path, op, value = a.get("data-path", ""), a.get("data-op", "truthy"), a.get("data-value", "")
        if not sch.PATH_RE.match(path):
            self.err(f"condition has an invalid path {path!r}")
            return False
        if op not in CONDITION_OPS:
            self.err(f"unknown condition operator {op!r}")
            return False
        if len(value) > 200:
            self.err("condition value is too long")
            return False
        flat, node, known = self.record_path(path)
        self.result.variables.add(flat)
        if not known:
            self.err(f"unknown variable {path!r} in condition")
        if self.mode == "clean":
            self.out.append(f'<div data-tp="if" data-path="{_escape_attr(path)}" '
                            f'data-op="{op}" data-value="{_escape_attr(value)}">')
            self.stack.append((tag, f"</{tag}>", False))
        else:
            self.out.append(
                f'{{% if tp_test({path_expr(path)}, "{op}", {jinja_string_literal(value)}) %}}'
            )
            self.stack.append((tag, "{% endif %}", False))
        return True

    # -- HTMLParser callbacks -----------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.skip_tag:
            if tag == self.skip_tag and tag not in VOID_TAGS:
                self.skip_depth += 1
            return
        a = self.attrs_dict(attrs)
        kind = a.get("data-tp")
        if tag in DROP_CONTENT_TAGS:
            if tag not in VOID_TAGS:
                self.start_skip(tag)
            return
        if kind in ("var", "const", "dynamic"):
            self.chip_inline(tag, a)
            if tag in VOID_TAGS:
                self._flush_chip()
            else:
                self.start_skip(tag)
            return
        if kind == "block":
            slug = a.get("data-slug", "")
            if not _SLUG_RE.match(slug):
                self.err(f"block has an invalid slug {slug!r}")
            else:
                self.result.blocks.add(slug)
                if self.known_blocks is not None and slug not in self.known_blocks:
                    self.err(f"unknown block {slug!r}")
                if self.mode == "clean":
                    self.out.append(f'<div data-tp="block" data-slug="{slug}"></div>')
                else:
                    self.out.append(f'{{% include "block:{slug}" %}}')
            if tag not in VOID_TAGS:
                self.start_skip(tag)
            return
        if kind == "repeat":
            if not self.open_repeat(a.get("data-path", ""), a.get("data-as", "item"),
                                    row_attrs=None, tag=tag):
                self.start_skip(tag)
            return
        if kind == "if":
            if not self.open_if(tag, a):
                self.start_skip(tag)
            return
        if tag == "tr" and a.get("data-tp-repeat"):
            if not self.open_repeat(a["data-tp-repeat"], a.get("data-tp-as") or "item",
                                    row_attrs=a, tag="tr"):
                self.start_skip(tag)
            return
        if tag not in ALLOWED_TAGS:
            return  # drop the tag, keep its content
        self.out.append(self.emit_tag(tag, a))
        if tag not in VOID_TAGS:
            self.stack.append((tag, f"</{tag}>", False))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS and self.skip_tag == tag.lower() and self.skip_depth == 1:
            self.skip_tag = None
            self.skip_depth = 0
            self._flush_chip()
        elif tag.lower() not in VOID_TAGS and self.stack and self.stack[-1][0] == tag.lower():
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if self.skip_depth == 0:
                    self.skip_tag = None
                    self._flush_chip()
            return
        if not any(t == tag for t, _, _ in self.stack):
            return  # stray end tag
        while self.stack:
            t, closer, pushed = self.stack.pop()
            self.out.append(closer)
            if pushed:
                self.scopes.pop()
            if t == tag:
                break

    def handle_data(self, data):
        if not self.skip_tag:
            self.out.append(_escape_text(data))
        elif self.pending_chip:
            self.chip_text.append(data)

    def handle_comment(self, data):  # drop comments
        pass

    def finish(self) -> CompileResult:
        self.close()
        self._flush_chip()
        while self.stack:
            _, closer, pushed = self.stack.pop()
            self.out.append(closer)
            if pushed:
                self.scopes.pop()
        self.result.source = "".join(self.out)
        return self.result


def compile_html(
    body: str,
    *,
    schema: dict | None = None,
    constants: set[str] | None = None,
    blocks: set[str] | None = None,
) -> CompileResult:
    """Compile editor HTML to Jinja source.

    ``schema=None`` skips variable validation (used for blocks that may be
    shared across template types). ``constants``/``blocks`` are sets of known
    keys/slugs; ``None`` skips those checks.
    """
    c = _Compiler(mode="jinja", schema=schema, constants=constants, blocks=blocks)
    c.feed(body or "")
    return c.finish()


def sanitize_html(body: str) -> str:
    """Return cleaned editor HTML with chips preserved (for storage / previews)."""
    c = _Compiler(mode="clean", schema=None, constants=None, blocks=None)
    c.feed(body or "")
    return c.finish().source


def validate_recorded(variables: set[str], schema: dict) -> list[str]:
    """Check recorded (flat) variable paths against ``schema``; return errors."""
    errors = []
    for flat in sorted(variables):
        if sch.resolve_flat(schema, flat) is None:
            errors.append(f"unknown variable {flat.replace('[]', '')!r}")
    return errors


def find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return a cycle (list of slugs) in a block include graph, or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    path: list[str] = []

    def visit(n: str) -> list[str] | None:
        color[n] = GREY
        path.append(n)
        for m in graph.get(n, ()):
            if color.get(m, WHITE) == GREY:
                return path[path.index(m):] + [m]
            if color.get(m, WHITE) == WHITE and m in graph:
                found = visit(m)
                if found:
                    return found
        path.pop()
        color[n] = BLACK
        return None

    for node in list(graph):
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None
