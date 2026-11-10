"""Template types: what each project can template, and how data gets in.

Each Django project registers its own template types, usually in a
``doctemplate_types.py`` module inside any installed app (auto-discovered)::

    from templates_pro import register, TemplateType, Var, Group, ListOf

    @register
    class InvoiceTemplate(TemplateType):
        key = "invoice"
        label = "Invoice"
        filename = "invoice-{invoice.number}"
        schema = {
            "invoice": Group("Invoice", {
                "number": Var("string", "Invoice number", sample="INV-0042"),
            }),
        }

        def build_context(self, invoice, **kwargs):
            return {"invoice": {"number": invoice.number}}

``build_context`` must return *plain data* (dicts, lists, str, numbers,
dates). Never return model instances; the engine rejects them.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

from .core.schema import SchemaError, sample_context, schema_to_json, validate_schema


class UnknownTemplateType(LookupError):
    pass


class TemplateType:
    key: str = ""
    label: str = ""
    description: str = ""
    schema: dict = {}
    #: Default filename pattern; tokens like ``{invoice.number}`` are filled in.
    filename: str = ""

    def build_context(self, obj: Any = None, **kwargs) -> dict:
        """Return plain-data context for ``obj``. Override in subclasses."""
        if obj is None or isinstance(obj, dict):
            return dict(obj or {}, **kwargs)
        raise NotImplementedError(
            f"{type(self).__name__}.build_context() must convert {type(obj).__name__} to a dict"
        )

    def sample_context(self) -> dict:
        """Data used for previews. Defaults to the schema's ``sample`` values."""
        return sample_context(self.schema)

    def get_locale(self, obj: Any = None) -> str | None:
        """Per-object locale (e.g. the customer's language). ``None`` = default."""
        return None

    def get_currency(self, obj: Any = None) -> str | None:
        """Per-object default currency for money values (e.g. the invoice currency).

        Used when a money chip has no explicit currency. ``None`` = site default.
        """
        return None

    def to_json(self) -> dict:
        return {
            "key": self.key,
            "label": str(self.label or self.key),
            "description": str(self.description or ""),
            "schema": schema_to_json(self.schema),
        }

    def __repr__(self):
        return f"<TemplateType {self.key}>"


_registry: dict[str, TemplateType] = {}


def register(cls_or_instance):
    """Class decorator (or plain call) registering a :class:`TemplateType`."""
    instance = cls_or_instance() if isinstance(cls_or_instance, type) else cls_or_instance
    if not isinstance(instance, TemplateType):
        raise ImproperlyConfigured("register() expects a TemplateType subclass or instance")
    if not instance.key:
        raise ImproperlyConfigured(f"{type(instance).__name__} must define 'key'")
    try:
        validate_schema(instance.schema)
    except SchemaError as exc:
        raise ImproperlyConfigured(f"Template type {instance.key!r}: {exc}") from exc
    existing = _registry.get(instance.key)
    if existing is not None and type(existing).__qualname__ != type(instance).__qualname__:
        raise ImproperlyConfigured(
            f"Template type key {instance.key!r} is registered twice "
            f"({type(existing).__qualname__} and {type(instance).__qualname__})"
        )
    _registry[instance.key] = instance
    return cls_or_instance


def unregister(key: str) -> None:
    _registry.pop(key, None)


def get_type(key: str) -> TemplateType:
    try:
        return _registry[key]
    except KeyError:
        raise UnknownTemplateType(
            f"Template type {key!r} is not registered. Is the app that defines it installed?"
        ) from None


def all_types() -> list[TemplateType]:
    return sorted(_registry.values(), key=lambda t: str(t.label or t.key).lower())


def type_choices() -> list[tuple[str, str]]:
    return [(t.key, str(t.label or t.key)) for t in all_types()]
