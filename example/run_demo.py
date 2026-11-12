#!/usr/bin/env python
"""Set up and start the demo with one command, from any folder:

    python example/run_demo.py              # http://127.0.0.1:8000  (admin / admin)
    python example/run_demo.py 8001         # extra arguments go to runserver

Each step only runs when it is needed:

1. If the dependencies are missing and no virtual environment is active, it creates
   `.venv` in the repository root (or reuses it) and restarts itself with that Python.
2. It installs the package (`pip install -e .`) when it is not importable.
3. It runs `migrate`, and `seed_demo` when the database has no templates yet.
4. It starts `runserver`.

To reload the demo content later: `python manage.py seed_demo --reset` (in example/).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parent
REPO = EXAMPLE.parent
VENV = REPO / ".venv"
REQUIRED = ("django", "jinja2", "babel", "html2text", "typst", "docx")


def missing_modules() -> list[str]:
    from importlib.util import find_spec

    return [name for name in REQUIRED if find_spec(name) is None]


def in_venv() -> bool:
    return sys.prefix != sys.base_prefix


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def ensure_dependencies() -> None:
    if not missing_modules():
        return
    if not in_venv():
        if not venv_python().exists():
            print(f"Creating a virtual environment in {VENV} ...")
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
        print(f"Restarting with {venv_python()}")
        sys.exit(subprocess.call([str(venv_python()), __file__, *sys.argv[1:]]))
    print("Installing django-templates-pro and its dependencies ...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(REPO)])


def setup_database() -> None:
    from django.core.management import call_command

    from templates_pro.models import DocumentTemplate

    call_command("migrate", interactive=False, verbosity=1)
    if not DocumentTemplate.objects.exists():
        call_command("seed_demo")


def main() -> None:
    if sys.version_info < (3, 10):
        sys.exit("The demo needs Python 3.10 or newer.")
    # runserver's autoreloader re-runs this script in a child process with RUN_MAIN set:
    # the parent has already done the setup.
    first_run = os.environ.get("RUN_MAIN") != "true"
    if first_run:
        ensure_dependencies()

    sys.path[:0] = [str(EXAMPLE), str(REPO / "src")]
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exampleproject.settings")
    import django
    from django.core.management import execute_from_command_line

    django.setup()
    if first_run:
        setup_database()
        print("\nDemo ready: log in with admin / admin. Docs at /docs/.\n")
    execute_from_command_line(["manage.py", "runserver", *sys.argv[1:]])


if __name__ == "__main__":
    main()
