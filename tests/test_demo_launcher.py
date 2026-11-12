"""`python -m templates_pro.demo`: copying the demo project out of the package."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from templates_pro import demo

REPO = Path(__file__).resolve().parents[1]


def test_copy_demo_has_project_and_docs(tmp_path):
    dest = tmp_path / "demo"
    demo.copy_demo(dest)
    assert (dest / "manage.py").is_file()
    assert (dest / "run_demo.py").is_file()
    assert (dest / "demo" / "samples" / "manifest.json").is_file()
    assert (dest / "_docs" / "README.md").is_file()
    assert (dest / "_docs" / "docs" / "index.md").is_file()
    assert (dest / "_docs" / "example" / "README.md").is_file()
    assert not (dest / "db.sqlite3").exists()
    assert not list(dest.rglob("__pycache__"))


def test_refuses_a_folder_that_is_not_a_demo(tmp_path):
    (tmp_path / "notes.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit):
        demo.main(["--dir", str(tmp_path)])
    assert [p.name for p in tmp_path.iterdir()] == ["notes.txt"]


def test_doc_files_match_the_wheel():
    """DOC_FILES (editable installs) and pyproject's force-include (wheels) list the same files."""
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    shipped = re.findall(r'^"([^"]+)" = "templates_pro/demo/project/_docs/', pyproject, flags=re.M)
    assert sorted(shipped) == sorted(demo.DOC_FILES)
