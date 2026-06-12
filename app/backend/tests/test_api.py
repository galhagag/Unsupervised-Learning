"""API-level regression tests (FastAPI TestClient)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import history  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    import main
    monkeypatch.setattr(main, "LIVE_FILE", tmp_path / "live_listings.json")
    with TestClient(main.app) as c:   # context manager runs the startup sync
        yield c


def test_empty_live_source_returns_zero_not_everything(client):
    """Regression: empty live pool used to fall through to ALL listings."""
    r = client.get("/api/opportunities?source=live")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_sample_and_researched_sources_disjoint(client):
    sample = client.get("/api/opportunities?source=sample").json()
    researched = client.get("/api/opportunities?source=researched").json()
    everything = client.get("/api/opportunities?source=all").json()
    assert sample["count"] == 9 and researched["count"] == 6
    assert everything["count"] == sample["count"] + researched["count"]


def test_sold_listing_excluded_from_opportunities(client):
    """Regression: sold/irrelevant history rows kept showing as opportunities."""
    r = client.post("/api/history/sic-001/status?status=sold")
    assert r.status_code == 200
    body = client.get("/api/opportunities?city=Sicily").json()
    assert all(l["id"] != "sic-001" for l in body["results"])
    assert body["closed_excluded"] >= 1
    # opt back in
    body = client.get("/api/opportunities?city=Sicily&include_closed=true").json()
    assert any(l["id"] == "sic-001" for l in body["results"])
    client.post("/api/history/sic-001/status?status=active")


def test_unknown_city_404_case_insensitive_match(client):
    assert client.get("/api/opportunities?city=Berlin").status_code == 404
    assert client.get("/api/opportunities?city=sofia").status_code == 200


def test_sort_by_score(client):
    body = client.get("/api/opportunities?sort=score").json()
    totals = [r["score"]["total"] for r in body["results"]]
    assert totals == sorted(totals, reverse=True)
