"""URL fetching for PDF (WeasyPrint) and DOCX images.

Templates are user-authored, so a template could point an ``<img>`` at an
internal address (SSRF) or at ``file:///etc/passwd``. The default fetcher
therefore only allows:

* ``data:`` URIs,
* files under ``STATIC_URL`` (via staticfiles finders / ``STATIC_ROOT``),
* files under ``MEDIA_URL`` (via the default storage),
* remote URLs starting with one of ``TEMPLATES_PRO["ALLOWED_URL_PREFIXES"]``.

Relative URLs such as ``/media/logo.png`` are resolved against
:data:`BASE_URL`, a pseudo host that only this fetcher understands.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.utils.module_loading import import_string

from .conf import tp_settings

BASE_URL = "http://templates-pro.local/"
_PSEUDO_HOST = "templates-pro.local"


class BlockedURL(ValueError):
    pass


def _local_file(path: str) -> Path | None:
    static_url = settings.STATIC_URL or "/static/"
    media_url = settings.MEDIA_URL or "/media/"
    if not static_url.startswith("/"):
        static_url = "/" + static_url
    if not media_url.startswith("/"):
        media_url = "/" + media_url
    if path.startswith(static_url):
        rel = path[len(static_url):]
        from django.contrib.staticfiles import finders

        found = finders.find(rel)
        if found:
            return Path(found)
        if settings.STATIC_ROOT:
            candidate = (Path(settings.STATIC_ROOT) / rel).resolve()
            if str(candidate).startswith(str(Path(settings.STATIC_ROOT).resolve())):
                return candidate if candidate.exists() else None
    if path.startswith(media_url):
        rel = path[len(media_url):]
        from django.core.files.storage import default_storage

        try:
            local = Path(default_storage.path(rel))  # raises for non-filesystem storages
        except (NotImplementedError, Exception):
            return None
        return local if local.exists() else None
    return None


def _media_bytes(path: str) -> bytes | None:
    """For non-filesystem storages (S3 etc.), read MEDIA files through the storage."""
    media_url = settings.MEDIA_URL or "/media/"
    if not media_url.startswith("/"):
        media_url = "/" + media_url
    if not path.startswith(media_url):
        return None
    from django.core.files.storage import default_storage

    rel = path[len(media_url):]
    if not default_storage.exists(rel):
        return None
    with default_storage.open(rel, "rb") as fh:
        return fh.read()


def _urlopen(url: str) -> dict:
    import urllib.request

    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - policy checked
        return {"string": resp.read(), "mime_type": resp.headers.get_content_type(),
                "redirected_url": url}


def safe_url_fetcher(url: str, *args, **kwargs) -> dict:
    """Fetch ``url`` if the policy allows it; raise :class:`BlockedURL` otherwise.

    Returns a dict with ``string`` (bytes), ``mime_type`` and ``redirected_url``
    (the classic WeasyPrint fetcher format; the PDF renderer adapts it to newer
    WeasyPrint versions automatically).
    """
    if url.startswith("data:"):
        return _urlopen(url)
    if url.startswith("/") and not url.startswith("//"):
        url = BASE_URL.rstrip("/") + url
    parsed = urlparse(url)
    if parsed.hostname == _PSEUDO_HOST:
        path = unquote(parsed.path)
        if ".." in path.split("/"):
            raise BlockedURL(url)
        local = _local_file(path)
        if local is not None:
            mime, _ = mimetypes.guess_type(local.name)
            return {"string": local.read_bytes(), "mime_type": mime, "redirected_url": url}
        data = _media_bytes(path)
        if data is not None:
            mime, _ = mimetypes.guess_type(path)
            return {"string": data, "mime_type": mime, "redirected_url": url}
        raise BlockedURL(f"not found or not allowed: {path}")
    allowed = tuple(tp_settings.ALLOWED_URL_PREFIXES or ())
    if parsed.scheme in ("http", "https") and allowed and url.startswith(allowed):
        return _urlopen(url)
    raise BlockedURL(f"URL not allowed in documents: {url}")


def get_url_fetcher(fmt: str | None = None):
    """The fetcher used for PDF and DOCX output (``TEMPLATES_PRO["URL_FETCHER"]``)."""
    if tp_settings.URL_FETCHER:
        return import_string(tp_settings.URL_FETCHER)
    return safe_url_fetcher
