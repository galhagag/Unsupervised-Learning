"""Tests for the timing planner, Monte Carlo, and paste-extraction features."""

import json
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import extractor  # noqa: E402
import history  # noqa: E402
import store  # noqa: E402
import timing  # noqa: E402

LISTINGS = json.loads(
    (Path(__file__).parent.parent / "data" / "listings.json").read_text())


def test_extract_heuristic_bulgarian():
    text = ("Тристаен апартамент, кв. Лозенец\nПродава се апартамент 92 кв.м "
            "на 4-ти етаж. Цена: 215 000 EUR.")
    l = extractor.extract(text, "Sofia")
    assert l["price_eur"] == 215000 and l["size_m2"] == 92
    assert l["data_source"] == "manual (pasted)"
    assert l["rent_basis"] == "city-level estimate"


def test_extract_stated_rent_wins():
    text = "Διαμέρισμα 75 τ.μ. στο Παγκράτι. Τιμή 230.000 EUR. rent 950 EUR"
    l = extractor.extract(text, "Athens")
    assert l["expected_monthly_rent_eur"] == 950
    assert l["rent_basis"] == "stated in listing"


def test_extract_bgn_conversion():
    text = "Двустаен апартамент 64 кв.м в Младост. Цена 273 000 лв за бърза продажба."
    l = extractor.extract(text, "Sofia")
    assert abs(l["price_eur"] - 273000 / 1.95583) < 2


@pytest.mark.parametrize("bad,msg", [
    ("short", "30+ chars"),
    ("A lovely apartment in the center with balcony and great morning light", "asking price"),
])
def test_extract_rejects(bad, msg):
    with pytest.raises(ValueError, match=re.escape(msg)):
        extractor.extract(bad, "Sofia")


def test_move_back_planner_accrues_years_abroad():
    prof = {**store.DEFAULT_PROFILE, "years_abroad_at_purchase": 5,
            "move_back_year": 2}
    plan = timing.move_back_planner(LISTINGS[0], prof)
    # 5y now + 2y until return = 7y => ordinary exemption
    assert plan["current_plan"]["exemption"] == "ordinary (5y)"
    # waiting until 10y abroad unlocks veteran and beats the current plan
    assert plan["best_plan"]["exemption"] == "veteran (10y)"
    assert plan["improvement_eur"] >= 0
    assert plan["improvement_ils"] > plan["improvement_eur"]


def test_six_year_cliff_note_fires_when_short():
    prof = {**store.DEFAULT_PROFILE, "years_abroad_at_purchase": 2,
            "move_back_year": 1}
    plan = timing.move_back_planner(LISTINGS[0], prof)
    assert "6-consecutive-years" in plan["six_year_cliff_note"]


def test_exit_optimizer_italy_cliff():
    it = next(l for l in LISTINGS if l["country"] == "italy")
    ex = timing.exit_optimizer(it, store.DEFAULT_PROFILE)
    y5 = next(r for r in ex["rows"] if r["sale_year"] == 5)
    y6 = next(r for r in ex["rows"] if r["sale_year"] == 6)
    assert y5["local_cgt"] > 0 and y6["local_cgt"] == 0


def test_monte_carlo_bands_ordered_and_deterministic():
    mc1 = timing.monte_carlo(LISTINGS[0], store.DEFAULT_PROFILE, draws=100)
    mc2 = timing.monte_carlo(LISTINGS[0], store.DEFAULT_PROFILE, draws=100)
    assert mc1["irr"]["p10"] <= mc1["irr"]["p50"] <= mc1["irr"]["p90"]
    assert mc1 == mc2                       # seeded => reproducible
    assert 0 <= mc1["prob_negative_cash_flow_pct"] <= 100


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "investments.db")
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    monkeypatch.setattr(extractor, "MANUAL_FILE", tmp_path / "manual.json")
    import main
    monkeypatch.setattr(main, "LIVE_FILE", tmp_path / "live.json")
    with TestClient(main.app) as c:
        yield c


def test_api_extract_save_and_analyze(client):
    r = client.post("/api/listings/extract", json={
        "text": "2-bed apartment 70 m2 in Kypseli, 3rd floor. Price €152,000.",
        "city": "Athens", "save": True})
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] and body["listing"]["price_eur"] == 152000
    assert body["score"]["total"] > 0
    # appears in the manual source and gets full analysis
    opp = client.get("/api/opportunities?source=manual").json()
    assert opp["count"] == 1
    assert opp["results"][0]["financials"]["after_tax_yield_pct"] is not None
    # and can be deleted
    lid = body["listing"]["id"]
    assert client.delete(f"/api/listings/manual/{lid}").status_code == 200
    assert client.get("/api/opportunities?source=manual").json()["count"] == 0


def test_api_extract_bad_input(client):
    assert client.post("/api/listings/extract",
                       json={"text": "x", "city": "Sofia"}).status_code == 400
    assert client.post("/api/listings/extract",
                       json={"text": "Price €100,000 flat " * 5,
                             "city": "Berlin"}).status_code == 400


def test_api_timing_and_montecarlo(client):
    t = client.get("/api/opportunities/sof-001/timing").json()
    assert t["move_back"]["rows"] and t["exit"]["rows"]
    mc = client.get("/api/opportunities/sof-001/montecarlo?draws=80").json()
    assert mc["draws"] == 80 and "p50" in mc["irr"]
    assert client.get("/api/opportunities/ghost/timing").status_code == 404
