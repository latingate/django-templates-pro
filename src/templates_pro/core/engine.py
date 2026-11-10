"""The sandboxed Jinja2 environment that renders compiled templates.

Defense in depth:

1. The compiler never emits user-controlled template syntax.
2. :class:`SafeEnvironment` (an ``ImmutableSandboxedEnvironment``) only allows
   attribute access on loop helpers and date/time values; everything else must
   be reached by dict subscripts.
3. :func:`ensure_plain` rejects contexts that contain anything other than
   plain data (dicts, lists, strings, numbers, dates…). ORM objects never
   reach a template.
4. Output size, loop length and wall-clock time are capped.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

from jinja2 import BaseLoader, ChainableUndefined, TemplateNotFound, pass_context
from jinja2.exceptions import SecurityError, TemplateError
from jinja2.runtime import LoopContext
from jinja2.sandbox import ImmutableSandboxedEnvironment

from .formatting import compare, format_value

MAX_LOOP_ITEMS = 10_000
DEFAULT_MAX_OUTPUT = 5_000_000  # characters
PLAIN_TYPES = (str, int, float, Decimal, bool, type(None), dt.date, dt.datetime, dt.time)


class TemplateRenderError(RuntimeError):
    pass


class UnsafeContextError(TypeError):
    pass


class RenderLimitError(TemplateRenderError):
    pass


def ensure_plain(value: Any, path: str = "context") -> None:
    """Raise :class:`UnsafeContextError` unless ``value`` is plain data."""
    if isinstance(value, PLAIN_TYPES):
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise UnsafeContextError(f"{path}: dict keys must be strings, got {k!r}")
            ensure_plain(v, f"{path}.{k}")
        return
    if isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            ensure_plain(v, f"{path}[{i}]")
        return
    raise UnsafeContextError(
        f"{path} is a {type(value).__module__}.{type(value).__name__}; template contexts may only "
        "contain dicts, lists, strings, numbers, booleans, None and date/time values. "
        "Convert model instances to dicts in TemplateType.build_context()."
    )


class SafeEnvironment(ImmutableSandboxedEnvironment):
    """Sandbox that allows attribute access only on a few harmless types."""

    SAFE_ATTRIBUTE_TYPES: tuple[type, ...] = (LoopContext, dt.date, dt.datetime, dt.time)

    def is_safe_attribute(self, obj, attr, value):
        if not super().is_safe_attribute(obj, attr, value):
            return False
        return isinstance(obj, self.SAFE_ATTRIBUTE_TYPES)

    def __init__(self, **kwargs):
        kwargs.setdefault("autoescape", True)
        kwargs.setdefault("undefined", ChainableUndefined)
        kwargs.setdefault("cache_size", 400)
        super().__init__(**kwargs)
        self._string_cache: OrderedDict[str, Any] = OrderedDict()

    def compile_cached(self, source: str):
        key = hashlib.sha1(source.encode("utf-8")).hexdigest()
        tpl = self._string_cache.get(key)
        if tpl is None:
            tpl = self.from_string(source)
            self._string_cache[key] = tpl
            if len(self._string_cache) > 256:
                self._string_cache.popitem(last=False)
        else:
            self._string_cache.move_to_end(key)
        return tpl


class BlockLoader(BaseLoader):
    """Resolves ``{% include "block:<slug>" %}``.

    ``fetch(slug)`` returns ``(compiled_source, uptodate)`` or ``None``;
    ``uptodate()`` returns ``False`` when the cached compiled block is stale.
    """

    def __init__(self, fetch: Callable[[str], tuple[str, Callable[[], bool]] | None]):
        self.fetch = fetch

    def get_source(self, environment, template):
        if not template.startswith("block:"):
            raise TemplateNotFound(template)
        found = self.fetch(template[len("block:"):])
        if found is None:
            raise TemplateNotFound(template)
        source, uptodate = found
        return source, None, uptodate


# ---------------------------------------------------------------------------
# Template globals
# ---------------------------------------------------------------------------


def _spec(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        spec = json.loads(raw or "{}")
    except ValueError:
        return {}
    return spec if isinstance(spec, dict) else {}


@pass_context
def tp_format(context, value, spec="{}"):
    return format_value(
        value,
        _spec(spec),
        locale=context.get("tp_locale") or "en_US",
        tz=context.get("tp_tz"),
        currency=context.get("tp_currency") or "USD",
    )


def tp_test(value, op, raw_other=""):
    other: Any = raw_other
    return compare(value, op, other)


def tp_iter(value) -> Iterable:
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_LOOP_ITEMS:
            raise RenderLimitError(f"a repeated list has more than {MAX_LOOP_ITEMS} items")
        return value
    return ()


def create_environment(
    *,
    fetch_block: Callable[[str], tuple[str, Callable[[], bool]] | None] | None = None,
    extra_globals: dict[str, Callable] | None = None,
) -> SafeEnvironment:
    env = SafeEnvironment(loader=BlockLoader(fetch_block) if fetch_block else None)
    env.globals.update(tp_format=tp_format, tp_test=tp_test, tp_iter=tp_iter)
    if extra_globals:
        env.globals.update(extra_globals)
    return env


def build_render_context(
    data: dict,
    *,
    constants: dict | None = None,
    locale: str = "en_US",
    tz: dt.tzinfo | None = None,
    currency: str = "USD",
    now: dt.datetime | None = None,
) -> dict:
    ensure_plain(data, "context")
    ensure_plain(constants or {}, "const")
    now = now or dt.datetime.now(tz or dt.timezone.utc)
    if tz is not None and now.tzinfo is not None:
        now = now.astimezone(tz)
    ctx = dict(data)
    ctx.update(
        const=dict(constants or {}),
        tp_now=now,
        tp_today=now.date(),
        tp_time=now.timetz(),
        tp_year=now.year,
        tp_locale=locale,
        tp_tz=tz,
        tp_currency=currency,
    )
    return ctx


def render_source(
    env: SafeEnvironment,
    source: str,
    context: dict,
    *,
    max_output: int = DEFAULT_MAX_OUTPUT,
    timeout: float | None = None,
) -> str:
    """Render compiled ``source`` with a prepared context (see build_render_context)."""
    deadline = (time.monotonic() + timeout) if timeout else None
    try:
        tpl = env.compile_cached(source)
        chunks: list[str] = []
        size = 0
        for chunk in tpl.generate(context):
            size += len(chunk)
            if size > max_output:
                raise RenderLimitError(f"rendered output exceeds {max_output} characters")
            if deadline and time.monotonic() > deadline:
                raise RenderLimitError(f"rendering took longer than {timeout} seconds")
            chunks.append(chunk)
        return "".join(chunks)
    except RenderLimitError:
        raise
    except RecursionError as exc:
        raise TemplateRenderError("blocks include each other in a loop") from exc
    except TemplateNotFound as exc:
        raise TemplateRenderError(f"missing block {exc.name!r}") from exc
    except SecurityError as exc:
        raise TemplateRenderError(f"blocked by the sandbox: {exc}") from exc
    except TemplateError as exc:
        raise TemplateRenderError(str(exc)) from exc


_FILENAME_TOKEN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\}")
_FILENAME_BAD = re.compile(r"[^\w.\- ]+", re.UNICODE)


def render_filename(pattern: str, context: dict, default: str = "document") -> str:
    """Fill ``{invoice.number}`` style tokens; result is filesystem-safe."""

    def lookup(match):
        value: Any = context
        for part in match.group(1).split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, (dt.date, dt.datetime)):
            value = value.isoformat()[:10]
        return "" if value is None else str(value)

    name = _FILENAME_TOKEN.sub(lookup, pattern or "")
    name = _FILENAME_BAD.sub("-", name).strip(" .-")
    return name[:150] or default
