"""The demo's documentation browser: every Markdown file of the repository, in reading order.

``SECTIONS`` fixes the order. A ``.md`` file that is not listed there still
appears, under "More", so new files never need registering.
"""

from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import Path

from django.urls import reverse

from .markdown import Markdown

# A demo copied by `python -m templates_pro.demo` keeps the Markdown files in its _docs/ folder.
_COPY = Path(__file__).resolve().parents[1] / "_docs"
REPO = _COPY if _COPY.is_dir() else Path(__file__).resolve().parents[2]

#: Where Markdown files are looked for (never node_modules, virtualenvs or build output).
SEARCH = ("*.md", "docs/**/*.md", "example/*.md", "frontend/*.md")

SECTIONS: list[tuple[str, list[str]]] = [
    ("Start here", [
        "README.md",
        "SETUP.md",
        "docs/installation.md",
        "docs/quickstart.md",
        "docs/samples.md",
        "example/README.md",
    ]),
    ("Writing templates", [
        "docs/concepts.md",
        "docs/editor.md",
        "docs/formatting.md",
        "docs/admin.md",
    ]),
    ("Integrating in your project", [
        "docs/template-types.md",
        "docs/rendering.md",
        "docs/settings.md",
        "docs/security.md",
        "docs/html-contract.md",
    ]),
    ("Running it", [
        "docs/commands.md",
        "docs/operations.md",
        "docs/troubleshooting.md",
    ]),
    ("Working on the package", [
        "docs/development.md",
        "frontend/README.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "docs/index.md",
    ]),
]


@dataclass
class Doc:
    path: str  # repository-relative, with forward slashes
    slug: str
    title: str
    section: str

    @property
    def url(self) -> str:
        return reverse("docs_page", args=[self.slug])


def _slug(path: str) -> str:
    name = path[:-3].lower()
    if name.startswith("docs/"):
        name = name[5:]
    return name.replace("/", "-").replace("_", "-").replace(".", "-")


def _title(path: str) -> str:
    try:
        with (REPO / path).open(encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return path


def catalogue() -> list[Doc]:
    """All Markdown files, ordered by ``SECTIONS`` and then alphabetically."""
    found = sorted({p.relative_to(REPO).as_posix() for pattern in SEARCH for p in REPO.glob(pattern)
                    if p.is_file()})
    docs, seen = [], set()
    for section, paths in SECTIONS:
        for path in paths:
            if path in found:
                docs.append(Doc(path, _slug(path), _title(path), section))
                seen.add(path)
    docs += [Doc(p, _slug(p), _title(p), "More") for p in found if p not in seen]
    return docs


def sections(docs: list[Doc]) -> list[tuple[str, list[Doc]]]:
    grouped: dict[str, list[Doc]] = {}
    for doc in docs:
        grouped.setdefault(doc.section, []).append(doc)
    return list(grouped.items())


def render(doc: Doc, docs: list[Doc]) -> tuple[str, list[tuple[int, str, str]]]:
    """Return (html, table of contents). Links between ``.md`` files point at this viewer."""
    by_path = {d.path: d for d in docs}

    def resolve(target: str) -> str | None:
        if target.startswith("#") or "://" in target or target.startswith("mailto:"):
            return target
        path, _, anchor = target.partition("#")
        full = posixpath.normpath(posixpath.join(posixpath.dirname(doc.path), path))
        other = by_path.get(full)
        if other is None:
            return None
        return other.url + (f"#{anchor}" if anchor else "")

    md = Markdown(resolve_link=resolve)
    body = md.convert((REPO / doc.path).read_text(encoding="utf-8"))
    return body, md.toc
