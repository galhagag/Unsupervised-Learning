"""HTTP Basic auth tests."""

import base64
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import extractor  # noqa: E402
import history  # noqa: E402
import store  # noqa: E402


def _basic(user, pwd):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "investments.db")
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "history.db")
    monkeypatch.setattr(extractor, "MANUAL_FILE", tmp_path / "manual.json")
    import main
    monkeypatch.setattr(main, "LIVE_FILE", tmp_path / "live.json")
    with TestClient(main.app) as c:
        yield c, main, monkeypatch


def test_open_when_no_password_configured(client):
    c, main, mp = client
    mp.setattr(main, "AUTH_PASSWORD", "")
    assert c.get("/api/cities").status_code == 200


def test_locked_when_password_set(client):
    c, main, mp = client
    mp.setattr(main, "AUTH_PASSWORD", "s3cret")
    r = c.get("/api/cities")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers          # triggers the browser prompt
    assert c.get("/", headers=_basic("gal", "wrong")).status_code == 401
    assert c.get("/api/cities", headers=_basic("notgal", "s3cret")).status_code == 401
    assert c.get("/api/cities", headers=_basic("gal", "s3cret")).status_code == 200


def test_garbage_auth_header_rejected(client):
    c, main, mp = client
    mp.setattr(main, "AUTH_PASSWORD", "s3cret")
    assert c.get("/api/cities", headers={"Authorization": "Basic %%%"}).status_code == 401
    assert c.get("/api/cities", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_health_stays_open_for_platform_checks(client):
    c, main, mp = client
    mp.setattr(main, "AUTH_PASSWORD", "s3cret")
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["auth_enabled"] is True
