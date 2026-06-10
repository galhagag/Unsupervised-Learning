"""Tests for the scoring engine and the historical-listings database."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import history  # noqa: E402
import scoring  # noqa: E402

LISTINGS = json.loads(
    (Path(__file__).parent.parent / "data" / "listings.json").read_text())


def by_id(lid):
    return next(l for l in LISTINGS if l["id"] == lid)


def test_score_shape_and_bounds():
    for l in LISTINGS:
        s = scoring.score(l)
        assert 0 <= s["total"] <= 100
        assert s["grade"][0] in "ABC"
        assert set(s["components"]) == {"location", "yield", "growth",
                                        "value", "liquidity"}
        assert all(0 <= v <= 100 for v in s["components"].values())
        assert -15 <= s["risk_adjustment"] <= 0


def test_area_matching():
    assert scoring.score(by_id("sof-001"))["area"] == "Lozenets"
    assert scoring.score(by_id("ath-001"))["area"] == "Koukaki / Acropolis"
    assert scoring.score(by_id("sic-003"))["area"] == "Syracuse - Ortigia"


def test_unmatched_neighborhood_uses_city_default():
    rogue = dict(by_id("sof-001"), neighborhood="Nowhere", title="Flat")
    s = scoring.score(rogue)
    assert s["area"] is None
    assert "city-default" in s["rationale"][0]


def test_no_short_let_penalty():
    koukaki = scoring.score(by_id("ath-001"))      # short let blocked
    kypseli = scoring.score(by_id("ath-002"))
    assert koukaki["risk_adjustment"] <= kypseli["risk_adjustment"] - 5


def test_cheaper_per_m2_scores_higher_value():
    base = by_id("ath-002")
    cheap = dict(base, price_eur=base["price_eur"] * 0.8)
    assert (scoring.score(cheap)["components"]["value"]
            > scoring.score(base)["components"]["value"])


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    return history


def _scores(listings):
    return {l["id"]: scoring.score(l) for l in listings}


def test_history_sync_and_query(db):
    db.sync(LISTINGS, _scores(LISTINGS))
    rows = db.query()
    assert len(rows) == len(LISTINGS)
    assert all(r["status"] == "active" and r["relevant"] for r in rows)
    assert rows[0]["score"]["grade"]            # snapshot stored


def test_manual_status_survives_resync(db):
    db.sync(LISTINGS, _scores(LISTINGS))
    assert db.set_status("sof-001", "sold", "closed at asking")
    db.sync(LISTINGS, _scores(LISTINGS))        # must NOT resurrect
    row = next(r for r in db.query() if r["id"] == "sof-001")
    assert row["status"] == "sold" and not row["relevant"]
    assert db.set_status("sof-001", "active")
    row = next(r for r in db.query() if r["id"] == "sof-001")
    assert row["relevant"]


def test_invalid_status_rejected(db):
    with pytest.raises(ValueError):
        db.set_status("sof-001", "exploded")


def test_vanished_live_listing_gets_delisted(db):
    from scrapers.common import to_listing
    live = to_listing(portal="homes.bg", portal_id="x9", city="Sofia",
                      title="Vanishing flat 60 m2", price_eur=120000,
                      size_m2=60, url="https://homes.bg/offer/x9")
    db.sync([live], _scores([live]))
    # next successful Sofia refresh no longer contains it
    db.sync([], {}, seen_live_ids=set(), refreshed_cities={"Sofia"})
    row = next(r for r in db.query() if r["id"] == live["id"])
    assert row["status"] == "delisted" and not row["relevant"]


def test_curated_listings_never_delisted_by_refresh(db):
    db.sync(LISTINGS, _scores(LISTINGS))
    db.sync([], {}, seen_live_ids=set(), refreshed_cities={"Sofia"})
    row = next(r for r in db.query() if r["id"] == "sof-001")
    assert row["status"] == "active"


def test_query_filters(db):
    db.sync(LISTINGS, _scores(LISTINGS))
    db.set_status("ath-001", "irrelevant")
    sofia = db.query(city="Sofia")
    assert sofia and all(r["city"] == "Sofia" for r in sofia)
    relevant_only = db.query(include_irrelevant=False)
    assert all(r["id"] != "ath-001" for r in relevant_only)
