"""Configure the PDF renderer from settings (called at startup and on setting changes)."""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured

from .conf import tp_settings
from .core.renderers import register_renderer

PDF_ENGINES = ("typst", "weasyprint")


def typst_themes() -> dict[str, dict[str, str]]:
    """Typst styles for project themes: THEMES[key]["typst"] = {"base": "modern", ...}."""
    from .core.renderers.typst_pdf import THEMES

    out: dict[str, dict[str, str]] = {}
    for key, theme in (tp_settings.THEMES or {}).items():
        spec = dict(theme.get("typst") or {})
        base = spec.pop("base", None) or ("minimal" if key not in THEMES else key)
        out[key] = {**THEMES.get(base, {}), **spec}
    return out


def configure() -> None:
    engine = tp_settings.PDF_ENGINE
    if engine not in PDF_ENGINES:
        raise ImproperlyConfigured(f"TEMPLATES_PRO['PDF_ENGINE'] must be one of {PDF_ENGINES}")
    if engine == "weasyprint":
        from .core.renderers.pdf import WeasyPrintRenderer

        register_renderer(WeasyPrintRenderer())
    else:
        from .core.renderers.typst_pdf import TypstPdfRenderer

        register_renderer(TypstPdfRenderer(
            font_paths=list(tp_settings.TYPST_FONT_PATHS or []),
            ignore_system_fonts=bool(tp_settings.TYPST_IGNORE_SYSTEM_FONTS),
            themes=typst_themes(),
        ))
