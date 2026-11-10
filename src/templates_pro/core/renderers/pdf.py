from __future__ import annotations

from . import Renderer, RendererUnavailable, RenderInput, build_document_html


class PdfRenderer(Renderer):
    """PDF via WeasyPrint (``pip install django-templates-pro[pdf]``)."""

    name = "pdf"
    mimetype = "application/pdf"
    extension = "pdf"
    label = "PDF"

    def is_available(self) -> bool:
        try:
            import weasyprint  # noqa: F401
        except (ImportError, OSError):  # OSError: missing system libraries (Pango)
            return False
        return True

    def render(self, doc: RenderInput) -> bytes:
        try:
            from weasyprint import HTML
        except (ImportError, OSError) as exc:
            raise RendererUnavailable(
                "PDF output needs WeasyPrint: pip install 'django-templates-pro[pdf]' "
                "(and its system libraries, see the WeasyPrint docs)."
            ) from exc
        kwargs = {"string": build_document_html(doc, for_print=True)}
        if doc.base_url:
            kwargs["base_url"] = doc.base_url
        if doc.url_fetcher:
            kwargs["url_fetcher"] = adapt_fetcher(doc.url_fetcher)
        # presentational_hints: honour HTML attributes such as <img width>.
        return HTML(**kwargs).write_pdf(presentational_hints=True)


def adapt_fetcher(func):
    """Wrap a classic ``url_fetcher(url) -> dict`` for WeasyPrint >= 68's URLFetcher API."""
    try:
        from weasyprint.urls import URLFetcher, URLFetcherResponse
    except ImportError:  # older WeasyPrint: plain functions are the API
        return func
    if isinstance(func, URLFetcher):
        return func

    class _Adapter(URLFetcher):
        def fetch(self, url, headers=None):
            res = func(url)
            body = res.get("string")
            if body is None:
                body = res.get("file_obj")
            hdrs = {"Content-Type": res["mime_type"]} if res.get("mime_type") else {}
            return URLFetcherResponse(res.get("redirected_url") or url, body=body, headers=hdrs)

    return _Adapter()
