import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def invoice_data():
    import datetime as dt
    from decimal import Decimal

    return {
        "invoice": {
            "number": "INV-7",
            "date": dt.date(2026, 3, 4),
            "total": Decimal("1999.9"),
            "discount": 0.15,
            "lines": [
                {"description": "Design", "qty": 2, "price": Decimal("500")},
                {"description": "Build <script>", "qty": 1, "price": Decimal("999.9")},
            ],
        },
        "customer": {"name": "Acme & Sons"},
    }
