"""Typst PDF engine and right-to-left support."""

import io
import zipfile

import pytest
from django.test import override_settings

from templates_pro import services
from templates_pro.core.formatting import direction_for
from templates_pro.core.renderers import PageSettings, RenderInput, get_renderer
from templates_pro.core.renderers.docx import parse_html
from templates_pro.core.renderers.typst_pdf import TypstPdfRenderer, TypstWriter, margins, tstr
from templates_pro.models import DocumentTemplate, TemplateBlock

V = '<span data-tp="var" data-path="{}">x</span>'


def typst_source(html, **kw):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        return TypstPdfRenderer().build_source(RenderInput(body_html=html, **kw), Path(tmp))


def pdf_text(pdf: bytes) -> str:
    from pypdf import PdfReader  # installed with typst? fall back to raw bytes

    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)


def test_typst_is_the_default_pdf_engine():
    assert isinstance(get_renderer("pdf"), TypstPdfRenderer)


@pytest.mark.parametrize("text", [
    '#import "x": *', "#read(\"/etc/passwd\")", "]#panic(1)[", '"\\"', "$x^2$", "*b* _i_ @ref ~ -- ---",
    "= heading", "// comment", "/* c */", "\\#escaped",
])
def test_document_text_is_never_typst_code(text):
    src = TypstWriter(lambda s: None, None).blocks(parse_html(f"<p>{text}</p>").children)
    assert src == "#" + tstr(text)  # one string literal, nothing else
    pdf = get_renderer("pdf").render(RenderInput(body_html=f"<p>{text}</p>"))
    assert pdf.startswith(b"%PDF")


def test_angle_brackets_stay_text():
    src = TypstWriter(lambda s: None, None).blocks(parse_html("<p>&lt;label&gt; &amp;</p>").children)
    assert src == "#" + tstr("<label> &")


def test_string_literal_escaping():
    assert tstr('a"b\\c') == '"a\\"b\\\\c"'


def test_rtl_document_settings():
    src = typst_source("<p>שלום</p>", direction="rtl", lang="he")
    assert '#set text(lang: "he", dir: rtl)' in src and "#let tp-rtl = true" in src


def test_page_setup_and_footer():
    src = typst_source("<p>x</p>", page=PageSettings(size="Letter", orientation="landscape",
                                                    margin="10mm 20mm"),
                       footer_html='<p>Page <span class="tp-page-number"></span></p>')
    assert 'paper: "us-letter"' in src and "flipped: true" in src
    assert "counter(page).display()" in src
    assert margins(PageSettings(margin="1cm 2cm 3cm")) == "(top: 1cm, right: 2cm, bottom: 3cm, left: 2cm)"


def test_tables_headers_spans_and_fills():
    html = ('<table><tbody><tr><th><p>A</p></th><th><p>B</p></th></tr>'
            '<tr><td colspan="2" style="background-color: #fde68a"><p>wide</p></td></tr></tbody></table>')
    src = typst_source(html)
    assert "header-rows: 1" in src and "table.header(" in src
    assert 'table.cell(colspan: 2, fill: rgb("#fde68a"))' in src


def test_bad_style_values_are_dropped():
    src = typst_source('<p><span style="color: red); #panic(); (; font-size: 9999zz">x</span></p>')
    assert "panic" not in src.replace(tstr("x"), "")


def test_images_from_data_uri():
    png = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
           "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    pdf = get_renderer("pdf").render(RenderInput(body_html=f'<p><img src="{png}" width="40"></p>'))
    assert pdf.startswith(b"%PDF")


def test_hebrew_text_survives_to_pdf():
    pdf = get_renderer("pdf").render(RenderInput(
        body_html="<h1>חשבונית</h1><table><tbody><tr><td><p>פריט</p></td><td><p>₪500</p></td></tr></tbody></table>",
        direction="rtl", lang="he"))
    try:
        text = pdf_text(pdf)
    except ImportError:
        pytest.skip("pypdf not installed")
    assert "חשבונית" in text and "פריט" in text


@pytest.mark.parametrize("locale,direction,expected", [
    ("he_IL", "auto", "rtl"), ("ar", "auto", "rtl"), ("fa-IR", "auto", "rtl"),
    ("en_GB", "auto", "ltr"), ("he_IL", "ltr", "ltr"), ("en_US", "rtl", "rtl"), (None, "auto", "ltr"),
])
def test_direction_for(locale, direction, expected):
    assert direction_for(locale, direction) == expected


@pytest.mark.django_db
def test_template_direction_reaches_every_format(invoice_data):
    t = DocumentTemplate(name="He", slug="he", template_type="invoice", locale="he_IL",
                         body="<p>חשבונית " + V.format("invoice.number") + "</p>",
                         output_formats=["html", "pdf", "docx", "txt"])
    t.full_clean()
    t.save()
    html = services.render(t, data=invoice_data, fmt="html").text
    assert '<html lang="he" dir="rtl">' in html
    docx = services.render(t, data=invoice_data, fmt="docx").content
    xml = zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml").decode()
    assert "<w:bidi/>" in xml and "<w:rtl/>" in xml
    assert services.render(t, data=invoice_data, fmt="pdf").content.startswith(b"%PDF")
    assert "חשבונית INV-7" in services.render(t, data=invoice_data, fmt="txt").text
    t.direction = "ltr"
    t.save()
    assert 'dir="ltr"' in services.render(t, data=invoice_data, fmt="html").text


@pytest.mark.django_db
def test_rtl_docx_tables_and_alignment():
    from templates_pro.core.renderers.docx import DocxRenderer

    body = ('<p style="text-align: right">ימין</p><table><tbody><tr><td><p>א</p></td>'
            '<td><p>ב</p></td></tr></tbody></table>')
    xml = zipfile.ZipFile(io.BytesIO(DocxRenderer().render(
        RenderInput(body_html=body, direction="rtl")))).read("word/document.xml").decode()
    assert "<w:bidiVisual/>" in xml
    assert 'w:jc w:val="left"' in xml  # visual right == logical start in a bidi paragraph


@pytest.mark.django_db
def test_header_and_footer_blocks_in_typst(invoice_data):
    ft = TemplateBlock.objects.create(
        name="F", slug="f", category="footer",
        body='<p>עמוד <span data-tp="dynamic" data-key="page_number">p</span></p>')
    t = DocumentTemplate.objects.create(name="T", slug="t", template_type="invoice",
                                        body="<p>x</p>", output_formats=["pdf"], footer_block=ft)
    assert services.render(t, data=invoice_data, fmt="pdf").content.startswith(b"%PDF")


def test_project_theme_typst_style():
    from templates_pro.engines import typst_themes

    with override_settings(TEMPLATES_PRO={"THEMES": {"brand": {
            "label": "Brand", "css": "templates_pro/themes/modern.css",
            "typst": {"base": "modern", "accent": 'rgb("#0f766e")'}}}}):
        themes = typst_themes()
        assert themes["brand"]["accent"] == 'rgb("#0f766e")'
        assert themes["brand"]["th-fill"] == 'rgb("#2563eb")'  # inherited from modern
        renderer = get_renderer("pdf")
        assert renderer.render(RenderInput(body_html="<p>x</p>", theme="brand")).startswith(b"%PDF")


def test_weasyprint_engine_switch():
    with override_settings(TEMPLATES_PRO={"PDF_ENGINE": "weasyprint"}):
        assert get_renderer("pdf").engine == "weasyprint"
    assert get_renderer("pdf").engine == "typst"


def test_invalid_engine_rejected():
    from django.core.exceptions import ImproperlyConfigured

    from templates_pro import engines

    with override_settings(TEMPLATES_PRO={"PDF_ENGINE": "typst"}):
        pass
    with pytest.raises(ImproperlyConfigured):
        with override_settings(TEMPLATES_PRO={"PDF_ENGINE": "wkhtml"}):
            pass
    engines.configure()


@pytest.mark.parametrize("text,expected", [
    ("שלום world", "rtl"), ("4 Canal Wharf", "ltr"), ("123 ₪", None), ("  (שלום)", "rtl"),
])
def test_first_strong(text, expected):
    from templates_pro.core.renderers.typst_pdf import first_strong

    assert first_strong(text) == expected


def test_english_paragraph_in_rtl_document_stays_ltr():
    src = typst_source("<p>4 Canal Wharf</p><p>שלום</p>", direction="rtl", lang="he")
    assert '#text(dir: ltr)[#"4 Canal Wharf"]' in src
    assert '#"שלום"' in src and "#text(dir: rtl)" not in src
