from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from templates_pro import registry, services
from templates_pro.models import DocumentTemplate, SiteConstant, TemplateBlock
from templates_pro.samples import loader

pytestmark = pytest.mark.django_db


def run(*args):
    out = StringIO()
    call_command("templates_pro_samples", *args, stdout=out)
    return out.getvalue()


def test_load_creates_valid_content():
    out = run()
    data = loader.manifest()
    assert "23 created" in out
    assert SiteConstant.objects.count() == len(data["constants"]) == 10
    assert TemplateBlock.objects.count() == len(data["blocks"]) == 7
    assert DocumentTemplate.objects.count() == len(data["templates"]) == 6
    for obj in [*TemplateBlock.objects.all(), *DocumentTemplate.objects.all()]:
        assert obj.slug.startswith("sample-")
        obj.full_clean()
    hebrew = DocumentTemplate.objects.get(slug="sample-invoice-hebrew")
    assert (hebrew.locale, hebrew.direction) == ("he_IL", "rtl")
    assert hebrew.footer_block.slug == "sample-page-footer-he"


def test_every_sample_renders_in_every_format_with_sample_data():
    run()
    for tpl in DocumentTemplate.objects.all():
        for fmt in tpl.output_formats:
            doc = services.render(tpl, fmt=fmt, sample=True)
            assert doc.content, (tpl.slug, fmt)
    html = services.render("sample-invoice-standard", fmt="html", sample=True).text
    assert "INV-2026-0042" in html and "Northwind Studio Ltd" in html and "Jane Roe" in html
    assert "data:image/png;base64," in html  # the logo needs no static files
    pdf = services.render("sample_invoice", fmt="pdf", sample=True)  # the type's default
    assert pdf.content.startswith(b"%PDF")


def test_sample_types_render_plain_dicts():
    run()
    doc = services.render("sample-order-confirmation", fmt="txt", data={
        "order": {"number": "A-1", "items": [], "item_count": 0},
        "customer": {"name": "Dana"},
    })
    assert "A-1" in doc.text


def test_rerun_keeps_edits_and_overwrite_resets_them():
    run()
    SiteConstant.objects.filter(key="company_name").update(value="My Company")
    tpl = DocumentTemplate.objects.get(slug="sample-welcome-letter")
    original = tpl.body
    tpl.body = "<p>Edited</p>"
    tpl.save()

    assert "0 created" in run()
    tpl.refresh_from_db()
    assert tpl.body == "<p>Edited</p>"

    run("--overwrite")
    tpl.refresh_from_db()
    assert tpl.body == original
    # Constants may be the project's own values: never overwritten.
    assert SiteConstant.objects.get(key="company_name").value == "My Company"


def test_does_not_touch_the_projects_own_content():
    own_block = TemplateBlock.objects.create(name="Mine", slug="page-footer", body="<p>mine</p>")
    own = DocumentTemplate(name="Mine", slug="invoice-standard", template_type="invoice",
                           body="<p>mine</p>", is_default=True)
    own.save()
    run("--overwrite")
    run("--remove")
    own.refresh_from_db()
    own_block.refresh_from_db()
    assert own.body == "<p>mine</p>" and own.is_default and own_block.body == "<p>mine</p>"


def test_remove_keeps_blocks_still_in_use():
    run()
    DocumentTemplate(name="Mine", slug="mine", template_type="invoice",
                     body='<div data-tp="block" data-slug="sample-signature"></div>').save()
    out = run("--remove")
    assert "Kept block sample-signature" in out
    assert list(TemplateBlock.objects.values_list("slug", flat=True)) == ["sample-signature"]
    assert list(DocumentTemplate.objects.values_list("slug", flat=True)) == ["mine"]
    assert SiteConstant.objects.count() == 10


def test_needs_the_samples_app(monkeypatch):
    for key in ("sample_invoice", "sample_letter", "sample_order", "sample_certificate"):
        monkeypatch.delitem(registry._registry, key)
    with pytest.raises(CommandError, match="templates_pro.samples"):
        run()
    assert not DocumentTemplate.objects.exists()
