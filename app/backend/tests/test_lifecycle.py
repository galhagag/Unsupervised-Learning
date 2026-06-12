"""Tests for the projection, recommendation, store, and insights engines,
plus API coverage of the lifecycle endpoints."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import history  # noqa: E402
import insights  # noqa: E402
import projection  # noqa: E402
import recommend  # noqa: E402
import store  # noqa: E402

LISTINGS = json.loads(
    (Path(__file__).parent.parent / "data" / "listings.json").read_text())


def by_id(lid):
    return next(l for l in LISTINGS if l["id"] == lid)


# ---- projection ----------------------------------------------------------

def test_projection_shape_and_metrics():
    p = projection.ProfileAssumptions(move_back_year=4, years_abroad_at_purchase=5)
    out = projection.project(by_id("sof-001"), p)
    assert len(out["years"]) == 10
    assert out["metrics"]["irr_pct"] is not None
    assert "total_after_tax_profit" in out["metrics"]
    assert out["equity_invested"] > 0


def test_move_back_year_switches_regime():
    p = projection.ProfileAssumptions(move_back_year=4, years_abroad_at_purchase=5)
    out = projection.project(by_id("sof-001"), p)
    regimes = [y["scenario"] for y in out["years"]]
    assert regimes[0] == "abroad"           # before move-back
    assert regimes[3] != "abroad"           # year 4 onward taxed in Israel


def test_returning_resident_window_exempts():
    # 10+ years abroad => veteran 10-year exemption; move back year 1.
    p = projection.ProfileAssumptions(move_back_year=1, years_abroad_at_purchase=10,
                                      hold_years=8)
    out = projection.project(by_id("sof-001"), p)
    assert all(y["scenario"] == "returning_resident" for y in out["years"])
    assert out["exit"]["israeli_cgt"] == 0


def test_italy_five_year_cgt_free_at_exit():
    p = projection.ProfileAssumptions(hold_years=10)
    out = projection.project(by_id("sic-001"), p)
    assert out["exit"]["local_cgt"] == 0     # >5y hold in Italy


def test_short_hold_in_italy_is_taxed():
    p = projection.ProfileAssumptions(hold_years=3)
    out = projection.project(by_id("sic-001"), p)
    assert out["exit"]["local_cgt"] > 0      # sold within 5y


def test_leverage_changes_equity_and_irr():
    cash = projection.project(by_id("sof-001"), projection.ProfileAssumptions(ltv=0.0))
    levered = projection.project(by_id("sof-001"), projection.ProfileAssumptions(ltv=0.6))
    assert levered["equity_invested"] < cash["equity_invested"]


# ---- recommendation ------------------------------------------------------

def test_recommendation_picks_and_ranks():
    rec = recommend.recommend(LISTINGS, store.DEFAULT_PROFILE)
    assert rec["top_pick"] is not None
    # Ranked by (affordable, fit): affordable group first, fit-desc within each.
    affordable_fits = [r["fit_score"] for r in rec["ranked"] if r["affordable"]]
    over_fits = [r["fit_score"] for r in rec["ranked"] if not r["affordable"]]
    assert affordable_fits == sorted(affordable_fits, reverse=True)
    assert over_fits == sorted(over_fits, reverse=True)
    # every affordable listing precedes every unaffordable one
    flags = [r["affordable"] for r in rec["ranked"]]
    assert flags == sorted(flags, reverse=True)
    assert len(rec["per_city"]) >= 1
    assert rec["rationale"]


def test_budget_flag_marks_affordability():
    prof = {**store.DEFAULT_PROFILE, "equity_budget_eur": 50000}
    rec = recommend.recommend(LISTINGS, prof)
    assert any(not r["affordable"] for r in rec["ranked"])


# ---- store (profile / deals / properties / ledger) -----------------------

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "investments.db")
    return store


def test_profile_roundtrip(db):
    assert db.get_profile()["hold_years"] == 10
    db.save_profile({"hold_years": 7, "move_back_year": 6})
    assert db.get_profile()["hold_years"] == 7
    assert db.get_profile()["move_back_year"] == 6


def test_deal_lifecycle(db):
    deal = db.create_deal(by_id("sic-001"))
    assert deal["id"] and deal["status"] == "active"
    db.update_deal_stage(deal["id"], "rogito", done=True, cost_eur=3000)
    got = db.get_deal(deal["id"])
    assert got["stages"]["rogito"]["done"] and got["stages"]["rogito"]["cost_eur"] == 3000
    db.set_deal_status(deal["id"], "completed")
    assert db.get_deal(deal["id"])["status"] == "completed"


def test_property_ledger_and_capex_basis(db):
    prop = db.create_property({"city": "Sicily", "country": "italy",
                               "title": "Test flat", "purchase_price_eur": 98000})
    db.add_ledger_entry(prop["id"], {"date": "2026-08-01", "kind": "rent", "amount_eur": 580})
    db.add_ledger_entry(prop["id"], {"date": "2026-09-01", "kind": "expense", "amount_eur": -200})
    p = db.add_ledger_entry(prop["id"], {"date": "2026-09-15", "kind": "capex",
                                         "amount_eur": -6000, "capex": True})
    assert p["totals"]["rent_income"] == 580
    assert p["totals"]["operating_expense"] == 200
    assert p["totals"]["capex_basis"] == 6000


# ---- insights ------------------------------------------------------------

def test_comparables(monkeypatch, tmp_path):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "h.db")
    c = insights.comparables(by_id("sof-001"), LISTINGS)
    assert c["peer_count"] >= 1 and "verdict" in c


def test_fx_overlay():
    assert insights.with_ils(1000) == round(1000 * insights.EUR_ILS)
    assert insights.with_ils(None) is None


# ---- API -----------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "investments.db")
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    import main
    monkeypatch.setattr(main, "LIVE_FILE", tmp_path / "live.json")
    with TestClient(main.app) as c:
        yield c


def test_api_profile_and_projection(client):
    assert client.put("/api/profile", json={"move_back_year": 3}).json()["move_back_year"] == 3
    proj = client.get("/api/opportunities/sof-001/projection").json()
    assert proj["metrics"]["irr_pct"] is not None


def test_api_sensitivity_lowers_returns(client):
    base = client.get("/api/opportunities/sof-001/projection").json()
    stressed = client.get("/api/opportunities/sof-001/projection?rent_pct=-15").json()
    assert stressed["metrics"]["total_after_tax_profit"] < base["metrics"]["total_after_tax_profit"]


def test_api_recommendation_and_memo(client):
    rec = client.get("/api/recommendation").json()
    assert rec["top_pick"]["id"]
    memo = client.get(f"/api/opportunities/{rec['top_pick']['id']}/memo").json()
    assert "Investment memo" in memo["markdown"]


def test_api_deal_and_property_flow(client):
    deal = client.post("/api/deals", json={"listing_id": "sic-001"}).json()
    assert deal["id"]
    upd = client.put(f"/api/deals/{deal['id']}/stages/rogito", json={"done": True})
    assert upd.json()["stages"]["rogito"]["done"]
    prop = client.post("/api/properties", json={"city": "Sicily", "country": "italy",
                                                "title": "X", "purchase_price_eur": 98000,
                                                "purchase_date": "2026-07-01"}).json()
    led = client.post(f"/api/properties/{prop['id']}/ledger",
                      json={"date": "2026-08-01", "kind": "capex", "amount_eur": -5000, "capex": True})
    assert led.json()["totals"]["capex_basis"] == 5000
    alerts = client.get("/api/alerts").json()["results"]
    assert any("Italy 5-year" in a["title"] for a in alerts)


def test_api_playbook_and_obligations(client):
    assert client.get("/api/playbooks/italy").json()["stages"]
    assert client.get("/api/playbooks/france").status_code == 404
    assert client.get("/api/obligations/greece").json()["israel_resident"]


def test_api_compare(client):
    r = client.post("/api/compare", json={"ids": ["sof-001", "sic-001"]}).json()
    assert r["count"] == 2
