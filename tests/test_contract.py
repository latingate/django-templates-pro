"""Editor ⇄ compiler contract.

tests/fixtures/editor_roundtrip/ holds the demo samples after a round trip
through the real TipTap editor schema (frontend/scripts/contract.mjs, run
with ``npm run contract``). If the editor's HTML output and the compiler ever
drift apart, these tests fail.
"""

import re
from pathlib import Path

import pytest

from templates_pro.core.compiler import compile_html

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "example" / "demo" / "samples"
FIXTURES = Path(__file__).parent / "fixtures" / "editor_roundtrip"
CASES = sorted(FIXTURES.glob("*.html"))


def _text(source: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", source))


@pytest.mark.skipif(not CASES, reason="run `npm run contract` in frontend/ first")
@pytest.mark.parametrize("fixture", CASES, ids=lambda p: p.stem)
def test_roundtrip_compiles_identically(fixture):
    kind, name = fixture.name.split("--", 1)
    original = compile_html((SAMPLES / kind / name).read_text(encoding="utf-8"))
    roundtrip = compile_html(fixture.read_text(encoding="utf-8"))
    assert roundtrip.ok, roundtrip.errors
    assert original.ok, original.errors
    assert roundtrip.variables == original.variables
    assert roundtrip.blocks == original.blocks
    assert roundtrip.constants == original.constants
    assert roundtrip.dynamic == original.dynamic
    assert _text(roundtrip.source) == _text(original.source)
    # Repeat/condition structure survives.
    for tag in ("{% for ", "{% if ", '{% include "block:'):
        assert roundtrip.source.count(tag) == original.source.count(tag)
