"""CONSTANTS_PROVIDER: values computed in code, available as constant chips.

Admin-edited SiteConstant rows and these are merged (these win on clashes)."""

from django.conf import settings


def provide(request=None):
    return {
        "site_url": request.build_absolute_uri("/") if request else "https://northwind.example",
        "time_zone": settings.TIME_ZONE,
    }
