"""django-templates-pro: WYSIWYG document templates for Django.

Public API (import from here or from :mod:`templates_pro.services`)::

    from templates_pro import register, TemplateType, Var, Group, ListOf
    from templates_pro.services import render, render_to_response, generate
"""

__version__ = "0.2.0"

__all__ = ["register", "TemplateType", "Var", "Group", "ListOf", "__version__"]


def __getattr__(name):
    # Lazy re-exports so ``import templates_pro`` never touches Django settings.
    if name in ("register", "TemplateType"):
        from . import registry

        return getattr(registry, name)
    if name in ("Var", "Group", "ListOf"):
        from .core import schema

        return getattr(schema, name)
    raise AttributeError(name)
