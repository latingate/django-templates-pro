"""Locale-aware value formatting (Babel) used by the ``tp_format`` filter.

A *format spec* is a small dict chosen in the editor's chip popover, e.g.::

    {"kind": "date", "style": "long"}
    {"kind": "date", "pattern": "dd/MM/yyyy"}
    {"kind": "money", "currency": "EUR", "decimals": 2}
    {"kind": "number", "decimals": 1}
    {"kind": "percent", "decimals": 0}
    {"kind": "text", "case": "upper"}
    {"kind": "boolean", "true": "Yes", "false": "No"}

Every spec may also carry ``"fallback"``: text shown when the value is empty.
Formatting never raises; on bad input it falls back to ``str(value)``.
"""

from __future__ import annotations

import datetime as dt
import decimal
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from babel import Locale, UnknownLocaleError
from babel import dates as bdates
from babel import numbers as bnumbers

log = logging.getLogger("templates_pro")

FORMAT_KINDS = ("auto", "text", "number", "money", "percent", "date", "datetime", "time", "boolean")
DATE_STYLES = ("short", "medium", "long", "full")
TEXT_CASES = ("none", "upper", "lower", "title", "capitalize")

#: Upper bound for user-chosen decimal places.
MAX_DECIMALS = 10


RTL_LANGUAGES = frozenset({"he", "iw", "ar", "fa", "ur", "yi", "ps", "sd", "ug", "dv", "ckb"})


def direction_for(locale: str | None, direction: str = "auto") -> str:
    """Resolve "auto"/"ltr"/"rtl" to "ltr" or "rtl" (auto = by the locale's language)."""
    if direction in ("ltr", "rtl"):
        return direction
    lang = (locale or "").replace("-", "_").split("_")[0].lower()
    return "rtl" if lang in RTL_LANGUAGES else "ltr"


def normalize_locale(code: str | None, default: str = "en_US") -> str:
    """Accept Django style (``en-us``) or Babel style (``en_US``) codes."""
    if not code:
        return default
    try:
        return str(Locale.parse(code.replace("-", "_")))
    except (ValueError, UnknownLocaleError):
        return default


def _is_empty(value: Any) -> bool:
    if value is None or value == "":
        return True
    # jinja2 Undefined instances are falsy and stringify to "" (or raise).
    return type(value).__name__.endswith("Undefined")


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _decimals(spec: dict) -> int | None:
    d = spec.get("decimals")
    if d is None or d == "":
        return None
    try:
        return max(0, min(int(d), MAX_DECIMALS))
    except (TypeError, ValueError):
        return None


def _number_pattern(decimals: int | None, base: str = "#,##0") -> str | None:
    if decimals is None:
        return None
    return base + ("." + "0" * decimals if decimals else "")


def _coerce_date(value: Any, want: str):
    if isinstance(value, str):
        try:
            value = dt.datetime.fromisoformat(value) if "T" in value or " " in value else (
                dt.date.fromisoformat(value) if want == "date" else dt.datetime.fromisoformat(value)
            )
        except ValueError:
            if want == "time":
                return dt.time.fromisoformat(value)
            raise
    if want == "date" and isinstance(value, dt.datetime):
        return value.date()
    if want == "time" and isinstance(value, dt.datetime):
        return value.timetz()
    return value


def format_value(
    value: Any,
    spec: dict | None = None,
    *,
    locale: str = "en_US",
    tz: dt.tzinfo | None = None,
    currency: str = "USD",
) -> str:
    spec = spec or {}
    if _is_empty(value):
        return str(spec.get("fallback", "") or "")
    kind = spec.get("kind") or "auto"
    try:
        if kind == "auto":
            kind = _infer_kind(value)
        handler = _HANDLERS.get(kind, _fmt_text)
        # Commercial rounding (1.5 -> 2), not Babel's default banker's rounding.
        with decimal.localcontext() as dctx:
            dctx.rounding = decimal.ROUND_HALF_UP
            return handler(value, spec, locale=locale, tz=tz, currency=currency)
    except Exception as exc:  # never break a document because of one value
        log.warning("templates_pro: could not format %r with %r: %s", value, spec, exc)
        return str(value)


def _infer_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dt.datetime):
        return "datetime"
    if isinstance(value, dt.date):
        return "date"
    if isinstance(value, dt.time):
        return "time"
    if isinstance(value, (int, float, Decimal)):
        return "number"
    return "text"


def _fmt_text(value, spec, **_):
    text = str(value)
    case = spec.get("case")
    if case == "upper":
        return text.upper()
    if case == "lower":
        return text.lower()
    if case == "title":
        return text.title()
    if case == "capitalize":
        return text[:1].upper() + text[1:]
    return text


def _fmt_number(value, spec, *, locale, **_):
    num = _decimal(value)
    if num is None:
        return str(value)
    return bnumbers.format_decimal(num, format=_number_pattern(_decimals(spec)), locale=locale)


def _fmt_money(value, spec, *, locale, currency, **_):
    num = _decimal(value)
    if num is None:
        return str(value)
    cur = (spec.get("currency") or currency or "USD").upper()
    decimals = _decimals(spec)
    pattern = None
    if decimals is not None or spec.get("symbol") == "code":
        pattern = Locale.parse(locale).currency_formats["standard"].pattern
        if decimals is not None:
            pattern = _currency_pattern(pattern, decimals)
        if spec.get("symbol") == "code":
            pattern = re.sub(r"¤(?=[#0])", "¤¤\xa0", pattern)  # "¤#" -> "¤¤ #"
            pattern = re.sub(r"(?<!¤)¤(?!¤)", "¤¤", pattern)  # remaining single ¤
    if pattern is None:
        return bnumbers.format_currency(num, cur, locale=locale)
    return bnumbers.format_currency(num, cur, format=pattern, locale=locale, currency_digits=False)


def _currency_pattern(pattern: str, decimals: int) -> str:
    """Rewrite a locale currency pattern (``¤#,##0.00``) to ``decimals`` digits."""
    out = []
    for part in pattern.split(";"):
        if "." in part:
            head, tail = part.split(".", 1)
            # keep any suffix after the zeros (e.g. " ¤")
            suffix = tail.lstrip("0#")
            out.append(head + ("." + "0" * decimals if decimals else "") + suffix)
        else:
            out.append(part)
    return ";".join(out)


def _fmt_percent(value, spec, *, locale, **_):
    num = _decimal(value)
    if num is None:
        return str(value)
    decimals = _decimals(spec)
    pattern = None if decimals is None else _number_pattern(decimals) + "%"
    return bnumbers.format_percent(num, format=pattern, locale=locale)


def _date_format(spec: dict) -> str:
    pattern = (spec.get("pattern") or "").strip()
    if pattern:
        return pattern
    style = spec.get("style") or "medium"
    return style if style in DATE_STYLES else "medium"


def _fmt_date(value, spec, *, locale, tz, **_):
    if isinstance(value, dt.datetime) and tz is not None and value.tzinfo is not None:
        value = value.astimezone(tz)
    value = _coerce_date(value, "date")
    return bdates.format_date(value, format=_date_format(spec), locale=locale)


def _fmt_datetime(value, spec, *, locale, tz, **_):
    value = _coerce_date(value, "datetime")
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        value = dt.datetime.combine(value, dt.time())
    if tz is not None and value.tzinfo is not None:
        value = value.astimezone(tz)
    return bdates.format_datetime(value, format=_date_format(spec), locale=locale)


def _fmt_time(value, spec, *, locale, tz, **_):
    if isinstance(value, dt.datetime) and tz is not None and value.tzinfo is not None:
        value = value.astimezone(tz)
    value = _coerce_date(value, "time")
    spec = {"style": "short", **spec}
    return bdates.format_time(value, format=_date_format(spec), locale=locale)


def _fmt_boolean(value, spec, **_):
    truthy = value if isinstance(value, bool) else str(value).lower() in ("1", "true", "yes", "y")
    return str(spec.get("true") or "Yes") if truthy else str(spec.get("false") or "No")


_HANDLERS = {
    "text": _fmt_text,
    "number": _fmt_number,
    "money": _fmt_money,
    "percent": _fmt_percent,
    "date": _fmt_date,
    "datetime": _fmt_datetime,
    "time": _fmt_time,
    "boolean": _fmt_boolean,
}


def compare(value: Any, op: str, other: Any = None) -> bool:
    """Condition test used by *if* sections. Never raises."""
    try:
        if op == "truthy":
            return not _is_empty(value) and bool(value)
        if op == "falsy":
            return _is_empty(value) or not bool(value)
        if op in ("eq", "ne"):
            a, b = value, other
            da, db = _decimal(a), _decimal(b)
            equal = (da == db) if (da is not None and db is not None) else (str(a) == str(b))
            return equal if op == "eq" else not equal
        if op in ("gt", "gte", "lt", "lte"):
            da, db = _decimal(value), _decimal(other)
            if da is None or db is None:
                return False
            return {"gt": da > db, "gte": da >= db, "lt": da < db, "lte": da <= db}[op]
        if op == "contains":
            return str(other) in str(value) if not isinstance(value, (list, tuple)) else (
                other in value
            )
    except Exception:
        return False
    return False


CONDITION_OPS = ("truthy", "falsy", "eq", "ne", "gt", "gte", "lt", "lte", "contains")
