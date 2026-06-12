"""Parser tests against recorded response shapes.

The live portals can't be reached from CI/sandboxes, so each parser is
verified against a fixture mirroring the portal's documented response
format. If a portal changes schema, update the fixture from a real
response and re-run.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers import api_next, homes_bg, spitogatos, refresh  # noqa: E402
from scrapers.common import parse_number, to_listing  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_api_next_parser():
    data = json.loads((FIXTURES / "api_next.json").read_text())
    listings = api_next.parse_results(data, portal="immobiliare.it",
                                      city="Sicily", max_results=6)
    # 3 rows in fixture; the EUR 15k parking spot must be filtered out
    assert len(listings) == 2
    first = listings[0]
    assert first["id"] == "immobiliare.it-119542876"
    assert first["price_eur"] == 129000
    assert first["size_m2"] == 95
    assert first["neighborhood"] == "Albergheria"
    assert first["listing_url"] == "https://www.immobiliare.it/annunci/119542876/"
    assert first["estimated"] is True
    assert first["expected_monthly_rent_eur"] == round(95 * 8.5)
    assert listings[1]["price_eur"] == 185000


def test_homes_bg_parser(monkeypatch):
    data = json.loads((FIXTURES / "homes_bg.json").read_text())
    monkeypatch.setattr(homes_bg, "fetch_json", lambda url, referer=None: data)
    listings, status = homes_bg.fetch(max_results=6)
    # 3 rows; the EUR 14.5k garage must be filtered out
    assert len(listings) == 2
    assert "OK, 2 listings" in status
    eur_flat, bgn_flat = listings
    assert eur_flat["price_eur"] == 139000          # '139 000' EUR parsed
    assert eur_flat["size_m2"] == 72
    assert eur_flat["neighborhood"] == "София, кв. Лозенец"
    assert eur_flat["listing_url"] == "https://www.homes.bg/offer/5j7Bx2a"
    # BGN converted at the fixed peg, area '98 m²' parsed, dict location
    assert bgn_flat["price_eur"] == round(265000 / 1.95583)
    assert bgn_flat["size_m2"] == 98
    assert bgn_flat["neighborhood"] == "София, кв. Младост 4"


def test_homes_bg_fetch_failure(monkeypatch):
    def boom(url, referer=None):
        raise ConnectionError("blocked")
    monkeypatch.setattr(homes_bg, "fetch_json", boom)
    listings, status = homes_bg.fetch()
    assert listings == []
    assert "fetch failed" in status


def test_spitogatos_jsonld_parser():
    html = (FIXTURES / "spitogatos.html").read_text()
    listings = spitogatos.parse_jsonld(html, max_results=6)
    assert len(listings) == 2
    first = listings[0]
    assert first["id"] == "spitogatos.gr-17223344"
    assert first["price_eur"] == 168000
    assert first["size_m2"] == 88                   # from "88 m²" in name
    assert first["city"] == "Athens"
    assert first["listing_url"] == "https://en.spitogatos.gr/property/17223344"


def test_spitogatos_challenge_page():
    assert spitogatos.parse_jsonld("<html><body>js challenge</body></html>", 6) == []


def test_refresh_fallback_chain(monkeypatch):
    """Athens: when indomio fails, spitogatos runs; statuses are chained."""
    from scrapers import indomio
    monkeypatch.setattr(indomio, "fetch",
                        lambda n=6: ([], "indomio.gr: no listings (blocked)"))
    fake = to_listing(portal="spitogatos.gr", portal_id="1", city="Athens",
                      title="Flat 70 m2", price_eur=200000, size_m2=70,
                      url="https://en.spitogatos.gr/property/1")
    monkeypatch.setattr(spitogatos, "fetch",
                        lambda n=6: ([fake], "spitogatos.gr: OK, 1 listings"))
    out = refresh(cities=["Athens"])
    assert len(out["listings"]) == 1
    assert "indomio.gr: no listings" in out["status"]["Athens"]
    assert "spitogatos.gr: OK" in out["status"]["Athens"]


def test_refresh_stops_chain_on_success(monkeypatch):
    from scrapers import indomio
    fake = to_listing(portal="indomio.gr", portal_id="2", city="Athens",
                      title="Flat 60 m2", price_eur=150000, size_m2=60,
                      url="https://www.indomio.gr/x")
    monkeypatch.setattr(indomio, "fetch",
                        lambda n=6: ([fake], "indomio.gr: OK, 1 listings"))
    called = []
    monkeypatch.setattr(spitogatos, "fetch",
                        lambda n=6: called.append(1) or ([], "x"))
    out = refresh(cities=["Athens"])
    assert len(out["listings"]) == 1 and not called


@pytest.mark.parametrize("raw,expected", [
    ("85", 85.0), ("85 m²", 85.0), ("139 000", 139000.0), ("139.000", 139000.0),
    ("139000", 139000.0), ("1.250,50", 1250.5), ("95,5", 95.5),
    (None, None), ("n/a", None), (120, 120.0),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_to_listing_filters_cheap_rows():
    assert to_listing(portal="p", portal_id="1", city="Sofia", title="parking",
                      price_eur=15000, size_m2=12, url="u") is None
