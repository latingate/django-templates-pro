"""Context schemas: declare which variables a template type exposes.

A schema is a plain ``dict`` mapping names to :class:`Var`, :class:`Group` or
:class:`ListOf` nodes::

    schema = {
        "invoice": Group("Invoice", {
            "number": Var("string", "Invoice number", sample="INV-0042"),
            "date": Var("date", "Invoice date", sample=date(2026, 1, 15)),
            "total": Var("money", "Total", sample=Decimal("1250.00")),
            "lines": ListOf("Line items", {
                "description": Var("string", "Description", sample="Consulting"),
                "qty": Var("number", "Quantity", sample=3),
            }),
        }),
    }

The schema drives three things: the variable picker in the editor, validation
when a template is saved, and sample data for previews.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

VAR_TYPES = (
    "string",
    "text",
    "integer",
    "number",
    "money",
    "percent",
    "date",
    "datetime",
    "time",
    "boolean",
    "email",
    "url",
)

#: Names the engine itself uses in the render context. Schema roots and loop
#: aliases may not use them.
RESERVED_NAMES = frozenset(
    {"const", "loop", "self", "super", "true", "false", "none", "True", "False", "None"}
)
RESERVED_PREFIX = "tp_"

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


@dataclass
class Var:
    """A single value (leaf)."""

    type: str = "string"
    label: str = ""
    sample: Any = None
    help: str = ""
    #: Default format spec used when the user did not choose one, e.g.
    #: ``{"kind": "money", "currency": "EUR"}``.
    format: dict | None = None

    def __post_init__(self):
        if self.type not in VAR_TYPES:
            raise ValueError(f"Unknown variable type {self.type!r}; use one of {VAR_TYPES}")


@dataclass
class Group:
    """A named group of fields (an object)."""

    label: str = ""
    fields: dict[str, Node] = field(default_factory=dict)
    help: str = ""


@dataclass
class ListOf:
    """A list of items; usable in *repeat* sections and repeated table rows."""

    label: str = ""
    item: dict[str, Node] = field(default_factory=dict)
    help: str = ""
    #: Sample items for previews. Generated from the item fields when omitted.
    sample: list | None = None
    sample_count: int = 3


Node = Var | Group | ListOf
Schema = dict  # dict[str, Node]


class SchemaError(ValueError):
    pass


def validate_schema(schema: Schema, _path: str = "") -> None:
    """Raise :class:`SchemaError` if names are invalid or reserved."""
    for name, node in schema.items():
        full = f"{_path}.{name}" if _path else name
        if not IDENT_RE.match(name):
            raise SchemaError(f"Invalid schema name {full!r}: use letters, digits and _")
        if not _path and (name in RESERVED_NAMES or name.startswith(RESERVED_PREFIX)):
            raise SchemaError(f"Schema root {name!r} is reserved")
        if isinstance(node, Group):
            validate_schema(node.fields, full)
        elif isinstance(node, ListOf):
            validate_schema(node.item, full)
        elif not isinstance(node, Var):
            raise SchemaError(f"{full!r} must be Var, Group or ListOf, got {type(node).__name__}")


def resolve(schema: Schema, path: str, scopes: dict[str, dict] | None = None) -> Node | None:
    """Find the node for a dotted ``path``.

    ``scopes`` maps loop aliases (``line``) to the item dict of the list they
    iterate, so ``line.description`` resolves inside a repeat section.
    """
    if not PATH_RE.match(path or ""):
        return None
    head, *rest = path.split(".")
    current: Any
    if scopes and head in scopes:
        current = Group(fields=scopes[head])
    elif head in schema:
        current = schema[head]
    else:
        return None
    for part in rest:
        if not isinstance(current, Group):
            return None
        current = current.fields.get(part)
        if current is None:
            return None
    return current


def merge_schemas(schemas: list[Schema]) -> Schema:
    """Union of several schemas (groups and list items are merged by name)."""
    out: dict[str, Node] = {}
    for schema in schemas:
        for name, node in schema.items():
            existing = out.get(name)
            if existing is None:
                out[name] = node
            elif isinstance(existing, Group) and isinstance(node, Group):
                out[name] = Group(existing.label, merge_schemas([existing.fields, node.fields]),
                                  existing.help)
            elif isinstance(existing, ListOf) and isinstance(node, ListOf):
                out[name] = ListOf(existing.label, merge_schemas([existing.item, node.item]),
                                   existing.help, existing.sample, existing.sample_count)
    return out


def resolve_flat(schema: Schema, flat_path: str) -> Node | None:
    """Resolve a *recorded* path such as ``invoice.lines[].description``.

    The compiler records variables used inside repeat sections in this form so
    they can be validated later against another schema (used for shared blocks).
    """
    current: Any = Group(fields=schema)
    for part in flat_path.split("."):
        is_item = part.endswith("[]")
        name = part[:-2] if is_item else part
        if not isinstance(current, Group):
            return None
        current = current.fields.get(name)
        if current is None:
            return None
        if is_item:
            if not isinstance(current, ListOf):
                return None
            current = Group(fields=current.item)
    return current


# ---------------------------------------------------------------------------
# Serialisation for the editor
# ---------------------------------------------------------------------------


def _node_json(name: str, node: Node, path: str) -> dict:
    if isinstance(node, Var):
        return {
            "kind": "var",
            "name": name,
            "path": path,
            "type": node.type,
            "label": str(node.label or name),
            "help": str(node.help or ""),
            "format": node.format or default_format(node.type),
        }
    if isinstance(node, Group):
        return {
            "kind": "group",
            "name": name,
            "path": path,
            "label": str(node.label or name),
            "help": str(node.help or ""),
            "children": [_node_json(n, c, f"{path}.{n}") for n, c in node.fields.items()],
        }
    return {
        "kind": "list",
        "name": name,
        "path": path,
        "label": str(node.label or name),
        "help": str(node.help or ""),
        # Item paths are relative: the editor prefixes them with the loop alias.
        "item": [_node_json(n, c, n) for n, c in node.item.items()],
    }


def schema_to_json(schema: Schema) -> list[dict]:
    return [_node_json(n, node, n) for n, node in schema.items()]


def default_format(var_type: str) -> dict:
    return {
        "integer": {"kind": "number", "decimals": 0},
        "number": {"kind": "number"},
        "money": {"kind": "money"},
        "percent": {"kind": "percent"},
        "date": {"kind": "date", "style": "medium"},
        "datetime": {"kind": "datetime", "style": "medium"},
        "time": {"kind": "time", "style": "short"},
        "boolean": {"kind": "boolean"},
    }.get(var_type, {"kind": "text"})


# ---------------------------------------------------------------------------
# Sample data for previews
# ---------------------------------------------------------------------------

_SAMPLES = {
    "string": "Sample text",
    "text": "Sample paragraph of longer text.",
    "integer": 7,
    "number": 12.5,
    "money": Decimal("1234.50"),
    "percent": 0.17,
    "date": _dt.date(2026, 1, 15),
    "datetime": _dt.datetime(2026, 1, 15, 14, 30),
    "time": _dt.time(9, 15),
    "boolean": True,
    "email": "jane@example.com",
    "url": "https://example.com",
}


def sample_value(node: Node, name: str = "") -> Any:
    if isinstance(node, Var):
        if node.sample is not None:
            return node.sample
        if node.type == "string" and name:
            return f"[{node.label or name}]"
        return _SAMPLES[node.type]
    if isinstance(node, Group):
        return {n: sample_value(c, n) for n, c in node.fields.items()}
    if node.sample is not None:
        return list(node.sample)
    return [
        {n: sample_value(c, n) for n, c in node.item.items()} for _ in range(node.sample_count)
    ]


def sample_context(schema: Schema) -> dict:
    return {name: sample_value(node, name) for name, node in schema.items()}
