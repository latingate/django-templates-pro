"""Load (or remove) the sample constants, blocks and templates.

The HTML in ``content/`` is exactly what the editor stores. Everything the
loader creates has a ``sample-`` slug, so it never touches a project's own
blocks and templates. Constants are only created when their key is missing and
are never changed or removed: they may be the project's own values.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction

CONTENT = Path(__file__).resolve().parent / "content"


class SamplesNotInstalled(RuntimeError):
    pass


@dataclass
class Summary:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)


def manifest() -> dict:
    return json.loads((CONTENT / "manifest.json").read_text(encoding="utf-8"))


def _require_types(data: dict) -> None:
    from ..registry import UnknownTemplateType, get_type

    try:
        for key in {t["type"] for t in data["templates"]}:
            get_type(key)
    except UnknownTemplateType as exc:
        raise SamplesNotInstalled(
            'Add "templates_pro.samples" to INSTALLED_APPS first: '
            "it registers the sample template types."
        ) from exc


def _formats(wanted: list[str]) -> list[str]:
    """The sample's formats that this project has enabled (at least one)."""
    from ..conf import tp_settings
    from ..core.renderers import all_renderers

    enabled = [f for f in tp_settings.OUTPUT_FORMATS if f in all_renderers()]
    return [f for f in wanted if f in enabled] or enabled[:1]


@transaction.atomic
def load_samples(*, overwrite: bool = False) -> Summary:
    """Create the sample content. Existing items are kept unless ``overwrite``."""
    from ..models import DocumentTemplate, SiteConstant, TemplateBlock

    data = manifest()
    _require_types(data)
    out = Summary()

    for c in data["constants"]:
        _, made = SiteConstant.objects.get_or_create(
            key=c["key"], defaults={"label": c["label"], "value": c["value"]})
        (out.created if made else out.skipped).append(f"constant {c['key']}")

    # Blocks may include blocks: the manifest lists dependencies first.
    for b in data["blocks"]:
        block = TemplateBlock.objects.filter(slug=b["slug"]).first()
        if block is not None and not overwrite:
            out.skipped.append(f"block {b['slug']}")
            continue
        (out.created if block is None else out.updated).append(f"block {b['slug']}")
        block = block or TemplateBlock(slug=b["slug"])
        block.name, block.category = b["name"], b["category"]
        block.template_types, block.description = b["types"], b["description"]
        block.body = (CONTENT / "blocks" / f"{b['slug']}.html").read_text(encoding="utf-8")
        block.full_clean()
        block.save()

    for t in data["templates"]:
        tpl = DocumentTemplate.objects.filter(slug=t["slug"]).first()
        if tpl is not None and not overwrite:
            out.skipped.append(f"template {t['slug']}")
            continue
        (out.created if tpl is None else out.updated).append(f"template {t['slug']}")
        tpl = tpl or DocumentTemplate(slug=t["slug"])
        tpl.name, tpl.template_type, tpl.theme = t["name"], t["type"], t["theme"]
        tpl.output_formats = _formats(t["formats"])
        tpl.margin = t.get("margin", "20mm")
        tpl.extra_css = t.get("extra_css", "")
        tpl.locale = t.get("locale", "")
        tpl.direction = t.get("direction", "auto")
        tpl.header_block = None
        tpl.footer_block = TemplateBlock.objects.filter(slug=t.get("footer")).first()
        # One default per type: leave an existing default (the user's choice) alone.
        other_default = (DocumentTemplate.objects.filter(template_type=t["type"], is_default=True)
                         .exclude(pk=tpl.pk).exists())
        tpl.is_default = bool(t.get("is_default")) and not other_default
        tpl.body = (CONTENT / "templates" / f"{t['slug']}.html").read_text(encoding="utf-8")
        tpl.full_clean()
        tpl.save()
    return out


@transaction.atomic
def remove_samples() -> Summary:
    """Delete the sample templates and blocks. Blocks still in use are kept."""
    from ..models import DocumentTemplate, TemplateBlock

    data = manifest()
    out = Summary()
    for t in data["templates"]:
        if DocumentTemplate.objects.filter(slug=t["slug"]).delete()[0]:
            out.removed.append(f"template {t['slug']}")
    # Reverse order: blocks that include other blocks go first.
    for b in reversed(data["blocks"]):
        block = TemplateBlock.objects.filter(slug=b["slug"]).first()
        if block is None:
            continue
        in_use = (TemplateBlock.used_in(block.slug) or block.header_for.exists()
                  or block.footer_for.exists())
        if in_use:
            out.kept.append(f"block {b['slug']}")
        else:
            block.delete()
            out.removed.append(f"block {b['slug']}")
    return out
