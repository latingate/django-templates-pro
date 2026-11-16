"""Hatch build hook: ship the demo website in the wheel, for ``python -m templates_pro.demo``.

Only for real wheels. In ``force-include`` (pyproject.toml), the files would also be copied
into site-packages by ``pip install -e .``, where the copy goes stale; editable installs use
``example/`` from the repository instead (see ``templates_pro/demo/__init__.py``).
"""

from __future__ import annotations

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PROJECT = "templates_pro/demo/project"

#: Repository path -> path in the wheel. The ``_docs/`` entries must match ``DOC_FILES``
#: in ``templates_pro/demo/__init__.py`` (tests/test_demo_launcher.py checks it).
DEMO_FILES = {
    "example": PROJECT,
    "README.md": f"{PROJECT}/_docs/README.md",
    "SETUP.md": f"{PROJECT}/_docs/SETUP.md",
    "CHANGELOG.md": f"{PROJECT}/_docs/CHANGELOG.md",
    "docs": f"{PROJECT}/_docs/docs",
    "example/README.md": f"{PROJECT}/_docs/example/README.md",
    "frontend/README.md": f"{PROJECT}/_docs/frontend/README.md",
}


class DemoBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name == "wheel" and version == "standard":
            build_data["force_include"].update(DEMO_FILES)
