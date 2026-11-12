"""Run the demo website from a pip install, in a folder of its own:

    python -m templates_pro.demo                    # http://127.0.0.1:8000  (admin / admin)
    python -m templates_pro.demo --dir mydemo 8001  # other folder; extra arguments go to runserver
    templates-pro-demo                              # the same, as a console script

The first run copies the demo project (``example/`` of the repository, shipped in the
wheel under ``project/``) into the folder. Every run then hands over to the copy's
``run_demo.py``: migrate, ``seed_demo`` on an empty database, runserver. The demo never
touches the current project or its database. Pure Python, no Django import here.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
#: The demo as shipped in the wheel (see ``force-include`` in pyproject.toml).
PACKAGED = HERE / "project"
#: The repository, for an editable install.
REPO = HERE.parents[2]
#: Files the demo's /docs/ page shows, copied into ``_docs/`` (keep in sync with pyproject.toml).
DOC_FILES = ("README.md", "SETUP.md", "CHANGELOG.md", "docs", "example/README.md", "frontend/README.md")
IGNORE = shutil.ignore_patterns("db.sqlite3", "__pycache__", "*.pyc", "media", "staticfiles", ".DS_Store")


def copy_demo(dest: Path) -> None:
    """Copy the demo project, with its documentation in ``dest/_docs``."""
    if (PACKAGED / "manage.py").is_file():
        shutil.copytree(PACKAGED, dest, ignore=IGNORE)
        return
    if not (REPO / "example" / "manage.py").is_file():
        raise FileNotFoundError("The demo project is missing from this installation.")
    shutil.copytree(REPO / "example", dest, ignore=IGNORE)
    for name in DOC_FILES:
        src, target = REPO / name, dest / "_docs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, target, ignore=IGNORE)
        elif src.is_file():
            shutil.copy2(src, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m templates_pro.demo",
        description="Set up and run the django-templates-pro demo website in its own folder.",
        epilog="Other arguments go to runserver, e.g. 8001 or 0.0.0.0:8000.",
    )
    parser.add_argument("--dir", default="templates-pro-demo",
                        help="folder for the demo (default: ./templates-pro-demo); reused if it exists")
    options, runserver_args = parser.parse_known_args(argv)

    dest = Path(options.dir).resolve()
    if not (dest / "manage.py").is_file():
        if dest.exists() and any(dest.iterdir()):
            parser.error(f"{dest} exists and is not a demo folder: choose another one with --dir")
        print(f"Copying the demo project to {dest}")
        copy_demo(dest)
    else:
        print(f"Using the demo in {dest} (delete the folder to start again)")
    try:
        return subprocess.call([sys.executable, str(dest / "run_demo.py"), *runserver_args])
    except KeyboardInterrupt:
        return 0
