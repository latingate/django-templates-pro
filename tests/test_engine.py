import datetime as dt

import pytest

from templates_pro.core import engine
from templates_pro.core.compiler import compile_html


@pytest.fixture
def env():
    blocks = {"b": "<b>{{ tp_format(customer[\"name\"]) }}</b>", "loop": '{% include "block:loop" %}'}
    return engine.create_environment(
        fetch_block=lambda s: (blocks[s], lambda: True) if s in blocks else None)


def ctx(data=None, **kw):
    return engine.build_render_context(data or {}, now=dt.datetime(2026, 5, 6, 7, 8,
                                                                  tzinfo=dt.timezone.utc), **kw)


@pytest.mark.parametrize("attack", [
    '{{ "".__class__.__mro__[1].__subclasses__() }}',
    "{{ tp_format.__globals__ }}",
    "{{ customer.__class__ }}",
    "{{ cycler.__init__.__globals__ }}",
    "{{ customer.items() }}",
])
def test_sandbox_blocks_python_escapes(env, attack):
    try:
        out = engine.render_source(env, attack, ctx({"customer": {"name": "x"}}))
    except engine.TemplateRenderError as exc:
        assert "sandbox" in str(exc)
        return
    assert "class" not in out and "function" not in out and "dict_items" not in out


def test_immutable_sandbox(env):
    with pytest.raises(engine.TemplateRenderError):
        engine.render_source(env, "{{ customer.update({'a': 1}) }}{{ [].append(1) }}",
                             ctx({"customer": {}}))


def test_context_must_be_plain():
    class Model:
        pass

    with pytest.raises(engine.UnsafeContextError, match="context.invoice"):
        engine.build_render_context({"invoice": Model()})


def test_autoescape(env):
    out = engine.render_source(env, '{{ tp_format(x) }}', ctx({"x": "<script>"}))
    assert out == "&lt;script&gt;"


def test_blocks_and_missing_values(env, invoice_data):
    out = engine.render_source(env, '{% include "block:b" %}|{{ tp_format(customer["no"]["x"]) }}|',
                               ctx(invoice_data))
    assert out == "<b>Acme &amp; Sons</b>||"


def test_include_loop_is_reported(env):
    with pytest.raises(engine.TemplateRenderError, match="loop"):
        engine.render_source(env, '{% include "block:loop" %}', ctx())


def test_output_limit(env):
    src = compile_html('<div data-tp="repeat" data-path="xs" data-as="x"><p>aaaaaaaaaa</p></div>')
    with pytest.raises(engine.RenderLimitError):
        engine.render_source(env, src.source, ctx({"xs": list(range(500))}), max_output=1000)


def test_dynamic_values(env):
    src = compile_html('<span data-tp="dynamic" data-key="year">y</span> '
                       '<span data-tp="dynamic" data-key="today" '
                       'data-format=\'{"kind":"date","pattern":"yyyy-MM-dd"}\'>t</span>').source
    assert engine.render_source(env, src, ctx()) == "2026 2026-05-06"


def test_filename():
    assert engine.render_filename("inv-{a.b}/{c}", {"a": {"b": "X 1"}}) == "inv-X 1"
    assert engine.render_filename("{missing}", {}) == "document"
