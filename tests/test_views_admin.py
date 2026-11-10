import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from templates_pro.models import DocumentTemplate, TemplateBlock

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = User.objects.create_superuser("admin", "a@example.com", "pw")
    client.force_login(user)
    return client


def test_live_preview_json(admin_client):
    body = '<p><span data-tp="var" data-path="customer.name">n</span></p>'
    r = admin_client.post(reverse("templates_pro:preview"), json.dumps(
        {"body": body, "template_type": "invoice", "theme": "modern"}),
        content_type="application/json")
    assert r.status_code == 200 and b"Jane Roe" in r.content


def test_live_preview_errors_shown(admin_client):
    r = admin_client.post(reverse("templates_pro:preview"),
                          {"body": '<span data-tp="var" data-path="nope.x">x</span>',
                           "template_type": "invoice"})
    assert b"cannot be rendered" in r.content


def test_preview_requires_permission(client):
    User.objects.create_user("u", password="pw")
    client.login(username="u", password="pw")
    r = client.post(reverse("templates_pro:preview"), {"body": ""})
    assert r.status_code == 403


def test_admin_pages_render(admin_client):
    TemplateBlock.objects.create(name="H", slug="h", body="<p>h</p>")
    t = DocumentTemplate.objects.create(name="T", slug="t", template_type="invoice",
                                        body="<p>x</p>", output_formats=["html", "pdf"])
    for url in (
        reverse("admin:templates_pro_documenttemplate_changelist"),
        reverse("admin:templates_pro_documenttemplate_add"),
        reverse("admin:templates_pro_documenttemplate_change", args=[t.pk]),
        reverse("admin:templates_pro_templateblock_add"),
        reverse("admin:templates_pro_siteconstant_changelist"),
        reverse("admin:templates_pro_generateddocument_changelist"),
    ):
        r = admin_client.get(url)
        assert r.status_code == 200, url
    page = admin_client.get(reverse("admin:templates_pro_documenttemplate_add")).content.decode()
    assert "templates-pro-editor.js" in page and "_tpconfig" in page
    r = admin_client.get(reverse("templates_pro:saved_preview", args=[t.pk, "pdf"]))
    assert r["Content-Type"] == "application/pdf"


def test_admin_save_via_form(admin_client):
    r = admin_client.post(reverse("admin:templates_pro_documenttemplate_add"), {
        "name": "Inv", "slug": "inv", "template_type": "invoice", "description": "",
        "body": '<p><span data-tp="var" data-path="invoice.number">n</span></p>',
        "output_formats": ["html", "pdf"], "theme": "classic", "locale": "",
        "filename_pattern": "", "page_size": "A4", "orientation": "portrait", "margin": "20mm",
        "extra_css": "", "is_active": "on",
    })
    assert r.status_code == 302, r.content.decode()[:2000]
    assert DocumentTemplate.objects.get(slug="inv").variables == ["invoice.number"]


def test_system_checks_clean():
    from django.core.management import call_command

    call_command("check")
