"""Document themes: CSS applied to HTML and PDF output (not DOCX).

Built-in themes live in ``static/templates_pro/themes/``. Projects add more via
``TEMPLATES_PRO["THEMES"]``::

    TEMPLATES_PRO = {"THEMES": {
        "brand": {"label": "Our brand", "css": "myapp/doc-themes/brand.css"},
    }}

``css`` is a static file path (found with Django's staticfiles finders) or an
absolute filesystem path.
"""

from __future__ import annotations

import functools
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BUILTIN_THEMES = {
    "classic": {"label": _("Classic (serif)"), "css": "templates_pro/themes/classic.css"},
    "modern": {"label": _("Modern (sans-serif, accent colour)"),
               "css": "templates_pro/themes/modern.css"},
    "minimal": {"label": _("Minimal"), "css": "templates_pro/themes/minimal.css"},
    "corporate": {"label": _("Corporate (banded tables)"),
                  "css": "templates_pro/themes/corporate.css"},
    "none": {"label": _("No theme (unstyled)"), "css": None},
}


def all_themes() -> dict[str, dict]:
    from .conf import tp_settings

    return {**BUILTIN_THEMES, **(tp_settings.THEMES or {})}


def theme_choices() -> list[tuple[str, str]]:
    return [(key, str(t.get("label") or key)) for key, t in all_themes().items()]


@functools.lru_cache(maxsize=64)
def _read_css(path: str) -> str | None:
    p = Path(path)
    if p.is_absolute():
        return p.read_text(encoding="utf-8") if p.exists() else None
    from django.contrib.staticfiles import finders

    found = finders.find(path)
    if found:
        return Path(found).read_text(encoding="utf-8")
    # Fall back to the package's own static dir (works without staticfiles app).
    local = Path(__file__).parent / "static" / path
    return local.read_text(encoding="utf-8") if local.exists() else None


def theme_css(key: str | None) -> str:
    theme = all_themes().get(key or "") or {}
    path = theme.get("css")
    if not path:
        return ""
    return _read_css(str(path)) or ""


def theme_exists(key: str) -> bool:
    theme = all_themes().get(key)
    if theme is None:
        return False
    return theme.get("css") is None or _read_css(str(theme["css"])) is not None


def clear_cache():
    _read_css.cache_clear()
