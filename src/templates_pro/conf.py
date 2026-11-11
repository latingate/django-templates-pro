"""Package settings, read from ``settings.TEMPLATES_PRO`` (a dict).

Only set what you change; everything else falls back to :data:`DEFAULTS`.
See docs/settings.md for the full reference.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.signals import setting_changed

DEFAULTS: dict[str, Any] = {
    # Formatting
    "DEFAULT_LOCALE": None,  # None -> settings.LANGUAGE_CODE
    "TIME_ZONE": None,  # None -> settings.TIME_ZONE
    "DEFAULT_CURRENCY": "USD",
    # Output
    "OUTPUT_FORMATS": ["html", "pdf", "docx", "txt"],  # formats this project enables
    "DEFAULT_OUTPUT_FORMATS": ["html", "pdf"],  # pre-selected for new templates
    "DEFAULT_THEME": "classic",
    "THEMES": {},  # extra themes: {"brand": {"label": "Brand", "css": "app/themes/brand.css"}}
    "DEFAULT_PAGE_SIZE": "A4",
    # PDF engine: "typst" (default; pure pip, full RTL) or "weasyprint" (full CSS; needs Pango)
    "PDF_ENGINE": "typst",
    "TYPST_FONT_PATHS": [],  # extra font folders for Typst (bundled Noto Sans/Hebrew always on)
    "TYPST_IGNORE_SYSTEM_FONTS": False,  # True = only bundled + TYPST_FONT_PATHS (reproducible)
    "DEFAULT_MARGIN": "20mm",
    # Data
    "CONSTANTS_PROVIDER": None,  # dotted path to callable(request=None) -> dict
    # Limits & security
    "RENDER_TIMEOUT": 15,  # seconds of template rendering (not PDF layout)
    "MAX_OUTPUT_CHARS": 5_000_000,
    "URL_FETCHER": None,  # dotted path; default: templates_pro.fetchers.safe_url_fetcher
    "ALLOWED_URL_PREFIXES": [],  # remote image/CSS URL prefixes allowed in PDF/DOCX
    "PREVIEW_PERMISSION": "templates_pro.change_documenttemplate",
    # Editor defaults (overridable per widget)
    "EDITOR": {"preset": "full", "skin": "default", "height": 460},
    # Storage of GeneratedDocument files
    "STORAGE": None,  # alias in settings.STORAGES; None -> default storage
    "UPLOAD_TO": "templates_pro/generated/%Y/%m/",
    "CACHE_ALIAS": "default",
}


class _Settings:
    def __getattr__(self, name: str) -> Any:
        if name not in DEFAULTS:
            raise AttributeError(f"Unknown templates_pro setting {name!r}")
        user = getattr(settings, "TEMPLATES_PRO", {}) or {}
        value = user.get(name, DEFAULTS[name])
        if name == "EDITOR":
            value = {**DEFAULTS["EDITOR"], **(value or {})}
        return value

    @property
    def locale(self) -> str:
        from .core.formatting import normalize_locale

        return normalize_locale(self.DEFAULT_LOCALE or settings.LANGUAGE_CODE)

    @property
    def tzinfo(self):
        import zoneinfo

        name = self.TIME_ZONE or (settings.TIME_ZONE if settings.USE_TZ else None)
        return zoneinfo.ZoneInfo(name) if name else None


tp_settings = _Settings()


def _reset(**kwargs):
    if kwargs.get("setting") == "TEMPLATES_PRO":
        from . import engines, themes

        themes.clear_cache()
        engines.configure()


setting_changed.connect(_reset)
