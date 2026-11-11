"""The demo's documentation browser: its Markdown converter and the order of the pages."""

from __future__ import annotations

import importlib.util
import posixpath
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "example" / "demo"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"demo_docs_{name}", DEMO / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


markdown = _load("markdown")


def convert(text: str, **kwargs) -> str:
    return markdown.Markdown(**kwargs).convert(text)


def test_headings_get_github_anchors():
    md = markdown.Markdown()
    out = md.convert("# Title\n\n## Text direction (RTL)\n\n## build_context\n\n## Text direction (RTL)\n")
    assert '<h2 id="text-direction-rtl">' in out
    assert '<h2 id="build_context">' in out
    assert '<h2 id="text-direction-rtl-1">' in out  # duplicates are numbered
    assert md.toc[1] == (2, "text-direction-rtl", "Text direction (RTL)")


def test_text_is_escaped_and_code_is_literal():
    out = convert("Use `{{ form.media }}` in `<head>`, not <script>alert(1)</script>.\n")
    assert "<code>{{ form.media }}</code>" in out and "<code>&lt;head&gt;</code>" in out
    assert "<script>" not in out and "&lt;script&gt;" in out
    out = convert("```html\n<b>**not bold**</b>\n```\n")
    assert '<pre><code class="language-html">&lt;b&gt;**not bold**&lt;/b&gt;</code></pre>' in out


def test_inline_marks_leave_identifiers_alone():
    out = convert("**Bold**, *italic* and templates_pro_validate or a_b_c stay as they are.\n")
    assert "<strong>Bold</strong>" in out and "<em>italic</em>" in out
    assert "templates_pro_validate" in out and "<em>" not in out.split("italic</em>")[1]


def test_lists_nest_and_hold_code_blocks():
    out = convert("1. First\n2. Second:\n   - inner\n     wrapped\n\n   ```bash\n   run me\n   ```\n3. Third\n")
    assert out.count("<ol>") == 1 and "<ul>\n<li>inner wrapped</li>\n</ul>" in out
    assert '<pre><code class="language-bash">run me</code></pre>' in out
    assert out.index("run me") < out.index("Third")


def test_tables_keep_pipes_inside_code():
    out = convert("| Key | Value |\n|---|---|\n| `a|b` | **x** |\n| only one |\n")
    assert "<th>Key</th><th>Value</th>" in out
    assert "<td><code>a|b</code></td><td><strong>x</strong></td>" in out
    assert "<td>only one</td><td></td>" in out


def test_links_are_resolved_or_dropped():
    def resolve(target):
        if ":" in target:
            return target  # absolute: left to the converter's scheme check
        return {"other.md": "/docs/other/"}.get(target)  # None = not a page of the viewer

    out = convert("[a](other.md) [b](missing.md) [c](https://example.com) [d](javascript:alert)\n",
                  resolve_link=resolve)
    assert '<a href="/docs/other/">a</a>' in out
    assert '<a href="https://example.com" target="_blank" rel="noopener noreferrer">c</a>' in out
    assert out.count("<a ") == 2  # b (unknown page) and d (unsafe scheme) are plain text
    assert "javascript" not in out and "missing.md" not in out


def test_every_doc_is_listed_and_its_links_resolve():
    """docs/index.md and the viewer's SECTIONS must cover every page, and links must work."""
    django = pytest.importorskip("django")
    assert django
    docs_module = _load_docs()
    docs = docs_module.catalogue()
    paths = {d.path for d in docs}
    assert len({d.slug for d in docs}) == len(docs)
    assert not [d.path for d in docs if d.section == "More"], "add new pages to SECTIONS in demo/docs.py"
    index = (REPO / "docs" / "index.md").read_text(encoding="utf-8")
    for doc in docs:
        if doc.path.startswith("docs/") and doc.path != "docs/index.md":
            assert f"({doc.path[5:]})" in index, f"{doc.path} is missing from docs/index.md"
    anchors = {}
    for doc in docs:
        md = markdown.Markdown()
        md.convert((REPO / doc.path).read_text(encoding="utf-8"))
        anchors[doc.path] = {anchor for _, anchor, _ in md.toc}
    for doc in docs:
        source = re.sub(r"```.*?```", "", (REPO / doc.path).read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"\]\(([^)\s]+)\)", source):
            if target.startswith(("http", "mailto:")):
                continue
            path, _, anchor = target.partition("#")
            full = posixpath.normpath(posixpath.join(posixpath.dirname(doc.path), path)) if path else doc.path
            assert full in paths, f"{doc.path}: link to {target} leaves the documentation"
            assert not anchor or anchor in anchors[full], f"{doc.path}: no heading for {target}"


def _load_docs():
    """Import example/demo/docs.py without installing the demo app."""
    package = type(sys)("demo_docs_pkg")
    package.__path__ = [str(DEMO)]
    sys.modules["demo_docs_pkg"] = package
    sys.modules["demo_docs_pkg.markdown"] = markdown
    spec = importlib.util.spec_from_file_location("demo_docs_pkg.docs", DEMO / "docs.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
