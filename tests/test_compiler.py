import pytest

from templates_pro.core import schema as S
from templates_pro.core.compiler import (
    compile_html,
    find_cycle,
    jinja_string_literal,
    sanitize_html,
    validate_recorded,
)

SCHEMA = {
    "invoice": S.Group("Invoice", {
        "number": S.Var("string"),
        "total": S.Var("money"),
        "lines": S.ListOf("Lines", {"qty": S.Var("integer"), "tags": S.ListOf("Tags", {
            "name": S.Var("string")})}),
    }),
}


def var(path, fmt=None):
    f = f" data-format='{fmt}'" if fmt else ""
    return f'<span data-tp="var" data-path="{path}"{f}>{path}</span>'


def test_variable_compiles_to_sandboxed_call():
    r = compile_html(f"<p>{var('invoice.number')}</p>", schema=SCHEMA)
    assert r.ok
    assert 'tp_format(invoice["number"]' in r.source
    assert r.variables == {"invoice.number"}


def test_default_format_comes_from_schema_type():
    r = compile_html(var("invoice.total"), schema=SCHEMA)
    assert "money" in r.source


def test_unknown_variable_is_an_error():
    r = compile_html(var("invoice.nope"), schema=SCHEMA)
    assert r.errors == ["unknown variable 'invoice.nope'"]


def test_group_is_not_a_value():
    assert compile_html(var("invoice"), schema=SCHEMA).errors


def test_literal_template_syntax_is_neutralised():
    r = compile_html("<p>{{ 7*7 }} {% if %} {# c #}</p>")
    assert "{{" not in r.source and "{%" not in r.source and "{#" not in r.source


def test_malicious_path_rejected():
    r = compile_html('<span data-tp="var" data-path="invoice.__class__ }}{{ x">x</span>',
                     schema=None)
    assert r.errors and "{{ x" not in r.source


def test_format_literal_cannot_close_expression():
    lit = jinja_string_literal('{"x": "}} {% evil %}"}')
    assert "}" not in lit and "{" not in lit and "%" not in lit


def test_bad_format_json_rejected():
    r = compile_html(var("invoice.number", "{not json"), schema=SCHEMA)
    assert r.errors


def test_repeat_rows_and_nested_scopes():
    html = (
        '<table><tr data-tp-repeat="invoice.lines" data-tp-as="line"><td>'
        + var("line.qty")
        + '<div data-tp="repeat" data-path="line.tags" data-as="tag">' + var("tag.name")
        + "</div></td></tr></table>"
    )
    r = compile_html(html, schema=SCHEMA)
    assert r.ok, r.errors
    assert "{% for line in tp_iter(invoice[\"lines\"]) %}<tr>" in r.source
    assert "{% for tag in tp_iter(line[\"tags\"]) %}" in r.source
    assert {"invoice.lines[].qty", "invoice.lines[].tags[].name"} <= r.variables


def test_alias_cannot_shadow_schema_root():
    r = compile_html('<div data-tp="repeat" data-path="invoice.lines" data-as="invoice"></div>',
                     schema=SCHEMA)
    assert r.errors


def test_row_number_outside_repeat_is_error():
    r = compile_html('<span data-tp="dynamic" data-key="row_number">#</span>')
    assert r.errors


def test_condition():
    r = compile_html('<div data-tp="if" data-path="invoice.total" data-op="gt" data-value="0">'
                     "<p>x</p></div>", schema=SCHEMA)
    assert r.ok and '{% if tp_test(invoice["total"], "gt", "0") %}' in r.source


def test_blocks_and_constants_recorded():
    r = compile_html('<div data-tp="block" data-slug="footer"></div>'
                     '<span data-tp="const" data-key="site_name">S</span>',
                     blocks={"footer"}, constants=set())
    assert r.blocks == {"footer"} and r.constants == {"site_name"}
    assert r.warnings  # constant not defined


def test_unknown_block_error():
    assert compile_html('<div data-tp="block" data-slug="nope"></div>', blocks=set()).errors


@pytest.mark.parametrize("html,bad", [
    ("<script>alert(1)</script>", "alert"),
    ('<p onclick="x()">a</p>', "onclick"),
    ('<a href="javascript:alert(1)">a</a>', "javascript"),
    ('<img src="x" onerror="y">', "onerror"),
    ('<p style="background:url(http://evil)">a</p>', "url("),
    ("<iframe src='//x'></iframe>", "iframe"),
    ('<img src="data:image/svg+xml;base64,PHN2Zz4=">', "svg"),
])
def test_sanitizer_strips_dangerous_markup(html, bad):
    assert bad not in compile_html(html).source
    assert bad not in sanitize_html(html)


def test_sanitize_keeps_chips_and_labels():
    out = sanitize_html('<p>Hi <span data-tp="var" data-path="a.b" class="x">Name</span></p>')
    assert out == '<p>Hi <span data-tp="var" data-path="a.b">Name</span></p>'


def test_allowed_formatting_survives():
    html = ('<p style="text-align: center"><strong>b</strong> <a href="https://x" '
            'target="_blank">l</a></p><table><tbody><tr><td colspan="2">c</td></tr></tbody></table>')
    out = compile_html(html).source
    assert 'style="text-align: center"' in out and 'colspan="2"' in out
    assert 'rel="noopener noreferrer"' in out


def test_validate_recorded():
    assert validate_recorded({"invoice.lines[].qty"}, SCHEMA) == []
    assert validate_recorded({"invoice.lines[].nope"}, SCHEMA)


def test_find_cycle():
    assert find_cycle({"a": {"b"}, "b": {"c"}, "c": set()}) is None
    assert find_cycle({"a": {"b"}, "b": {"a"}}) in (["a", "b", "a"], ["b", "a", "b"])
