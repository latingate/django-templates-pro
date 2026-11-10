import datetime as dt
from decimal import Decimal

import pytest

from templates_pro.core.formatting import compare, format_value, normalize_locale


@pytest.mark.parametrize("value,spec,locale,expected", [
    (dt.date(2026, 3, 4), {"kind": "date", "style": "long"}, "en_US", "March 4, 2026"),
    (dt.date(2026, 3, 4), {"kind": "date", "style": "long"}, "de_DE", "4. März 2026"),
    (dt.date(2026, 3, 4), {"kind": "date", "pattern": "dd/MM/yyyy"}, "en_US", "04/03/2026"),
    ("2026-03-04", {"kind": "date", "style": "short"}, "en_GB", "04/03/2026"),
    (Decimal("1234.5"), {"kind": "money", "currency": "EUR"}, "de_DE", "1.234,50\xa0€"),
    (Decimal("1234.5"), {"kind": "money", "currency": "USD", "decimals": 0}, "en_US", "$1,235"),
    (Decimal("1234.5"), {"kind": "money", "currency": "USD", "symbol": "code"}, "en_US",
     "USD\xa01,234.50"),
    (1234.567, {"kind": "number", "decimals": 1}, "en_US", "1,234.6"),
    (0.175, {"kind": "percent", "decimals": 1}, "en_US", "17.5%"),
    ("hello world", {"kind": "text", "case": "title"}, "en_US", "Hello World"),
    (True, {"kind": "boolean", "true": "Paid", "false": "Open"}, "en_US", "Paid"),
    (None, {"kind": "text", "fallback": "n/a"}, "en_US", "n/a"),
    ("not a number", {"kind": "number"}, "en_US", "not a number"),
])
def test_format_value(value, spec, locale, expected):
    assert format_value(value, spec, locale=locale) == expected


def test_money_uses_default_currency():
    assert format_value(Decimal("5"), {"kind": "money"}, locale="en_US", currency="GBP") == "£5.00"


def test_timezone_conversion():
    v = dt.datetime(2026, 1, 1, 23, 30, tzinfo=dt.timezone.utc)
    import zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Jerusalem")
    assert format_value(v, {"kind": "date", "pattern": "yyyy-MM-dd"}, tz=tz) == "2026-01-02"


def test_normalize_locale():
    assert normalize_locale("en-us") == "en_US"
    assert normalize_locale("he") == "he"
    assert normalize_locale("xx-nope", default="fr_FR") == "fr_FR"


@pytest.mark.parametrize("value,op,other,expected", [
    (5, "gt", "3", True), ("5", "lte", "3", False), ("", "truthy", "", False),
    (None, "falsy", "", True), ("Paid", "eq", "Paid", True), (Decimal("1.0"), "eq", "1", True),
    (["a"], "contains", "a", True), ("x", "gt", "abc", False),
])
def test_compare(value, op, other, expected):
    assert compare(value, op, other) is expected
