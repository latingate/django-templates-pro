import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from templates_pro import services
from templates_pro.models import DocumentTemplate, GeneratedDocument, SiteConstant, TemplateBlock
from templates_pro.registry import get_type

pytestmark = pytest.mark.django_db

V = '<span data-tp="var" data-path="{}">x</span>'


def make_block(slug, body, **kw):
    b = TemplateBlock(name=slug.title(), slug=slug, body=body, **kw)
    b.full_clean()
    b.save()
    return b


def make_template(body, slug="inv", **kw):
    kw.setdefault("output_formats", ["html", "pdf", "docx", "txt"])
    t = DocumentTemplate(name="Invoice", slug=slug, template_type="invoice", body=body, **kw)
    t.full_clean()
    t.save()
    return t


def test_render_html_with_blocks_constants_and_loops(invoice_data):
    SiteConstant.objects.create(key="site_name", label="Site", value="Peltransport")
    make_block("cust", "<p>To: " + V.format("customer.name") + "</p>", template_types=["invoice"])
    body = (
        "<h1>" + V.format("invoice.number") + "</h1>"
        '<div data-tp="block" data-slug="cust"></div>'
        '<p><span data-tp="const" data-key="site_name">S</span></p>'
        '<table><tr data-tp-repeat="invoice.lines" data-tp-as="l"><td>'
        + V.format("l.description") + "</td><td>" + V.format("l.price") + "</td></tr></table>"
    )
    t = make_template(body)
    doc = services.render(t, data=invoice_data, fmt="html")
    html = doc.text
    assert "INV-7" in html and "To: Acme &amp; Sons" in html and "Peltransport" in html
    assert "Build &lt;script&gt;" in html and "€999.90" in html
    assert doc.filename == "invoice-INV-7.html"


def test_block_edit_applies_everywhere(invoice_data):
    b = make_block("hdr", "<p>Old header</p>")
    t1 = make_template('<div data-tp="block" data-slug="hdr"></div>', slug="a")
    t2 = make_template('<div data-tp="block" data-slug="hdr"></div>', slug="b")
    assert "Old header" in services.render(t1, data=invoice_data, fmt="html").text
    b.body = "<p>New header</p>"
    b.save()
    for t in (t1, t2):
        assert "New header" in services.render(t, data=invoice_data, fmt="html").text


def test_inactive_block_renders_empty(invoice_data):
    make_block("x", "<p>secret</p>", is_active=False)
    t = make_template('<div data-tp="block" data-slug="x"></div>')
    assert "secret" not in services.render(t, data=invoice_data, fmt="html").text


def test_unknown_variable_rejected_on_clean():
    with pytest.raises(ValidationError) as exc:
        make_template(V.format("invoice.missing"))
    assert "unknown variable" in str(exc.value)


def test_block_variables_validated_against_including_template():
    make_block("rec", V.format("recipient.name"))  # a 'letter' variable
    with pytest.raises(ValidationError, match="recipient.name"):
        make_template('<div data-tp="block" data-slug="rec"></div>')


def test_block_cycle_detected():
    make_block("a", "<p>a</p>")
    make_block("b", '<div data-tp="block" data-slug="a"></div>')
    a = TemplateBlock.objects.get(slug="a")
    a.body = '<div data-tp="block" data-slug="b"></div>'
    with pytest.raises(ValidationError, match="loop"):
        a.full_clean()


def test_block_slug_protected_when_used():
    b = make_block("keep", "<p>k</p>")
    make_template('<div data-tp="block" data-slug="keep"></div>')
    b.slug = "renamed"
    with pytest.raises(ValidationError, match="slug"):
        b.full_clean()


def test_version_increments_on_change():
    t = make_template("<p>a</p>")
    assert t.version == 1
    t.body = "<p>b</p>"
    t.save()
    assert t.version == 2
    t.save()
    assert t.version == 2


def test_all_formats(invoice_data):
    footer = make_block("ft", '<p>Page <span data-tp="dynamic" data-key="page_number">p</span></p>',
                        category="footer")
    t = make_template("<h1>Hi " + V.format("customer.name") + "</h1>", footer_block=footer)
    pdf = services.render(t, data=invoice_data, fmt="pdf")
    assert pdf.content.startswith(b"%PDF") and pdf.mimetype == "application/pdf"
    docx = services.render(t, data=invoice_data, fmt="docx")
    assert docx.content[:2] == b"PK"
    txt = services.render(t, data=invoice_data, fmt="txt").text
    assert "Hi Acme & Sons" in txt


def test_format_must_be_enabled_on_template(invoice_data):
    t = make_template("<p>x</p>", output_formats=["html"])
    with pytest.raises(services.TemplateNotAvailable):
        services.render(t, data=invoice_data, fmt="pdf")


def test_default_template_lookup_by_type(invoice_data):
    make_template("<p>default</p>", is_default=True)
    assert "default" in services.render("invoice", data=invoice_data, fmt="html").text


def test_sample_render_and_locale():
    t = make_template(V.format("invoice.date"), locale="de_DE")
    assert "01.02.2026" in services.render(t, sample=True, fmt="html").text


def test_generate_creates_record(invoice_data, tmp_path):
    with override_settings(MEDIA_ROOT=str(tmp_path)):
        t = make_template("<p>" + V.format("invoice.number") + "</p>")
        rec = services.generate(t, data=invoice_data, fmt="pdf")
        assert isinstance(rec, GeneratedDocument)
        assert rec.size > 0 and len(rec.checksum) == 64 and rec.template_version == t.version
        assert rec.file.name.endswith(".pdf")


def test_constants_cache_invalidated():
    c = SiteConstant.objects.create(key="k", label="K", value="1")
    assert services.get_constants()["k"] == "1"
    c.value = "2"
    c.save()
    assert services.get_constants()["k"] == "2"


@override_settings(TEMPLATES_PRO={"CONSTANTS_PROVIDER": "tests.test_django.provider"})
def test_constants_provider():
    assert services.get_constants()["support_email"] == "help@example.com"


def provider(request=None):
    return {"support_email": "help@example.com"}


def test_preview_document():
    doc, errors = services.preview_document("<p>" + V.format("invoice.number") + "</p>", "invoice")
    assert not errors and "INV-0042" in doc.text
    _, errors = services.preview_document(V.format("invoice.zzz"), "invoice")
    assert errors


def test_unregistered_type_reported():
    t = DocumentTemplate(name="X", slug="x", template_type="ghost", body="")
    with pytest.raises(ValidationError, match="not registered"):
        t.full_clean()


def test_sample_context_from_schema():
    data = get_type("invoice").sample_context()
    assert data["invoice"]["number"] == "INV-0042"
    assert len(data["invoice"]["lines"]) == 3
    assert isinstance(data["invoice"]["date"], dt.date)


def test_pdf_fetcher_blocks_remote_and_file_urls(invoice_data):
    t = make_template('<p><img src="http://169.254.169.254/x.png">ok</p>')
    assert services.render(t, data=invoice_data, fmt="pdf").content.startswith(b"%PDF")
    from templates_pro.fetchers import BlockedURL, safe_url_fetcher

    for url in ("http://169.254.169.254/", "file:///etc/passwd",
                "http://templates-pro.local/static/../../etc/passwd"):
        with pytest.raises(BlockedURL):
            safe_url_fetcher(url)
    assert safe_url_fetcher(
        "http://templates-pro.local/static/templates_pro/themes/classic.css")["string"]
