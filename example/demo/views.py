from pathlib import Path

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from templates_pro.core.compiler import compile_html
from templates_pro.models import DocumentTemplate
from templates_pro.registry import get_type
from templates_pro.services import render as render_document
from templates_pro.services import render_to_response
from templates_pro.widgets import TemplateEditorWidget

from . import docs as docs_browser
from .models import Customer, Employee, Invoice, Order

# Which model feeds each template type in this project.
SOURCES = {
    "invoice": Invoice,
    "customer_letter": Customer,
    "order_confirmation": Order,
    "employment_certificate": Employee,
}
SAMPLES = Path(__file__).resolve().parent / "samples"


def index(request):
    rows = []
    for tpl in DocumentTemplate.objects.filter(is_active=True).order_by("template_type", "name"):
        model = SOURCES.get(tpl.template_type)
        objects = list(model.objects.all()[:4]) if model else []
        rows.append({"template": tpl, "objects": objects})
    return render(request, "demo/index.html", {"rows": rows})


def document(request, slug, pk, fmt):
    tpl = get_object_or_404(DocumentTemplate, slug=slug, is_active=True)
    model = SOURCES.get(tpl.template_type)
    if model is None or fmt not in (tpl.output_formats or []):
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    extra = {"sender": request.user} if tpl.template_type == "customer_letter" else {}
    return render_to_response(tpl, obj, fmt=fmt, attachment=fmt == "docx", request=request,
                              **extra)


class GalleryForm(forms.Form):
    """Four editors with different presets and skins, all bound to the invoice type."""

    full_default = forms.CharField(label="preset='full', skin='default'", widget=TemplateEditorWidget(
        template_type="invoice", preset="full", skin="default", height=360))
    simple_paper = forms.CharField(label="preset='simple', skin='paper'", widget=TemplateEditorWidget(
        template_type="invoice", preset="simple", skin="paper", height=360))
    minimal_dark = forms.CharField(label="preset='minimal', skin='dark' (select text for the bubble menu)",
                                   widget=TemplateEditorWidget(template_type="invoice",
                                                               preset="minimal", skin="dark",
                                                               height=220))
    custom_compact = forms.CharField(
        label="custom toolbar, skin='compact'",
        widget=TemplateEditorWidget(
            template_type="order_confirmation", skin="compact", height=220,
            toolbar=["bold", "italic", "|", "bulletList", "|", "variable", "dynamic", ">",
                     "preview"]))


@login_required
def editor_gallery(request):
    invoice_html = (SAMPLES / "templates" / "invoice-modern.html").read_text(encoding="utf-8")
    order_html = (SAMPLES / "templates" / "order-confirmation.html").read_text(encoding="utf-8")
    form = GalleryForm(initial={
        "full_default": invoice_html, "simple_paper": invoice_html,
        "minimal_dark": "<p>Hello <span data-tp=\"var\" data-path=\"customer.name\">Customer</span>, "
                        "select some text to see the bubble menu, or type {{ to insert a field.</p>",
        "custom_compact": order_html,
    })
    return render(request, "demo/gallery.html", {"form": form})


class LetterForm(forms.Form):
    customer = forms.ModelChoiceField(Customer.objects.all(), empty_label=None)
    body = forms.CharField(label="Your letter", widget=TemplateEditorWidget(
        template_type="customer_letter", preset="simple", skin="paper", height=420,
        placeholder="Write a letter… type {{ to insert the customer's name"))

    def clean_body(self):
        body = self.cleaned_data["body"]
        result = compile_html(body, schema=get_type("customer_letter").schema)
        if result.errors:
            raise ValidationError(result.errors)
        return body


@login_required
def user_letter(request):
    """A non-admin page where a user writes and renders their own template."""
    slug = f"user-{request.user.pk}-letter"
    tpl = DocumentTemplate.objects.filter(slug=slug).first()
    output = None
    if request.method == "POST":
        form = LetterForm(request.POST)
        if form.is_valid():
            tpl = tpl or DocumentTemplate(slug=slug, name=f"Letter by {request.user}",
                                          template_type="customer_letter")
            tpl.body = form.cleaned_data["body"]
            tpl.theme, tpl.output_formats = "classic", ["html", "pdf"]
            tpl.save()
            output = render_document(tpl, form.cleaned_data["customer"], fmt="html",
                                     request=request, sender=request.user).text
    else:
        form = LetterForm(initial={"body": tpl.body if tpl else (
            "<p>Dear <span data-tp=\"var\" data-path=\"customer.name\">Customer › Contact name</span>,</p>"
            "<p>…</p>")})
    return render(request, "demo/user_letter.html", {"form": form, "output": output, "tpl": tpl})


def docs_index(request):
    """Every Markdown file of the repository, grouped and in reading order."""
    docs = docs_browser.catalogue()
    return render(request, "demo/docs.html", {"sections": docs_browser.sections(docs)})


def docs_page(request, slug):
    docs = docs_browser.catalogue()
    position = next((i for i, d in enumerate(docs) if d.slug == slug), None)
    if position is None:
        raise Http404
    doc = docs[position]
    body, toc = docs_browser.render(doc, docs)
    return render(request, "demo/docs.html", {
        "sections": docs_browser.sections(docs), "doc": doc, "body": body,
        "toc": [(level, anchor, title) for level, anchor, title in toc if level in (2, 3)],
        "previous": docs[position - 1] if position else None,
        "next": docs[position + 1] if position + 1 < len(docs) else None,
    })
