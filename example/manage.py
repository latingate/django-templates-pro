#!/usr/bin/env python
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # In the repository, use the package from src/ without installing it.
    src = Path(__file__).resolve().parent.parent / "src"
    if (src / "templates_pro").is_dir():
        sys.path.insert(0, str(src))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exampleproject.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
