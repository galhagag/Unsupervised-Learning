"""Persistent store for investor profile, deals (acquisitions in progress),
owned properties, and their ledgers / capex logs.

Single-user app: one profile row (id=1). Deals and properties are keyed by
the originating listing id plus an autoincrement id so the same listing can
seed multiple deals over time.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "investments.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    stages TEXT NOT NULL DEFAULT '{}',     -- {stage_key: {done, note, cost_eur}}
    professionals TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active'   -- active | completed | abandoned
);
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER,
    listing_id TEXT,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    title TEXT NOT NULL,
    purchase_price_eur INTEGER,
    purchase_date TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    kind TEXT NOT NULL,        -- rent | expense | capex
    description TEXT,
    amount_eur REAL NOT NULL,  -- positive inflow, negative outflow
    capex INTEGER DEFAULT 0    -- 1 if it adds to CGT cost basis
);
"""

DEFAULT_PROFILE = {
    "years_abroad_at_purchase": 5,
    "move_back_year": 4,
    "marginal_rate": 0.47,
    "hold_years": 10,
    "equity_budget_eur": 120000,
    "rent_strategy": "long_let",
    "ltv": 0.0,
    "mortgage_rate": 0.045,
    "mortgage_term_years": 20,
    "rent_growth_pct": 2.5,
    "appreciation_pct": 3.0,
    "vacancy_pct": 5.0,
    "discount_rate_pct": 7.0,
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---- profile -------------------------------------------------------------

def get_profile() -> dict:
    with _connect() as c:
        row = c.execute("SELECT data FROM profile WHERE id=1").fetchone()
        if row:
            return {**DEFAULT_PROFILE, **json.loads(row["data"])}
        return dict(DEFAULT_PROFILE)


def save_profile(patch: dict) -> dict:
    merged = {**get_profile(), **{k: v for k, v in patch.items() if v is not None}}
    with _connect() as c:
        c.execute("INSERT INTO profile (id, data) VALUES (1, ?) "
                  "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                  (json.dumps(merged),))
    return merged


# ---- deals ---------------------------------------------------------------

def create_deal(listing: dict) -> dict:
    with _connect() as c:
        cur = c.execute(
            "INSERT INTO deals (listing_id, city, country, title, created_at) "
            "VALUES (?,?,?,?,?)",
            (listing["id"], listing["city"], listing["country"],
             listing["title"], _now()))
        deal_id = cur.lastrowid
    return get_deal(deal_id)


def get_deal(deal_id: int) -> dict | None:
    with _connect() as c:
        row = c.execute("SELECT * FROM deals WHERE id=?", (deal_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["stages"] = json.loads(d["stages"])
    d["professionals"] = json.loads(d["professionals"])
    return d


def list_deals() -> list[dict]:
    with _connect() as c:
        rows = c.execute("SELECT id FROM deals ORDER BY created_at DESC").fetchall()
    return [get_deal(r["id"]) for r in rows]


def update_deal_stage(deal_id: int, stage_key: str, done: bool | None = None,
                      note: str | None = None, cost_eur: float | None = None) -> dict | None:
    deal = get_deal(deal_id)
    if not deal:
        return None
    stage = deal["stages"].get(stage_key, {})
    if done is not None:
        stage["done"] = done
    if note is not None:
        stage["note"] = note
    if cost_eur is not None:
        stage["cost_eur"] = cost_eur
    deal["stages"][stage_key] = stage
    with _connect() as c:
        c.execute("UPDATE deals SET stages=? WHERE id=?",
                  (json.dumps(deal["stages"]), deal_id))
    return get_deal(deal_id)


def set_deal_status(deal_id: int, status: str) -> dict | None:
    with _connect() as c:
        c.execute("UPDATE deals SET status=? WHERE id=?", (status, deal_id))
    return get_deal(deal_id)


# ---- properties + ledger -------------------------------------------------

def create_property(p: dict) -> dict:
    with _connect() as c:
        cur = c.execute(
            "INSERT INTO properties (deal_id, listing_id, city, country, title,"
            " purchase_price_eur, purchase_date, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (p.get("deal_id"), p.get("listing_id"), p["city"], p["country"],
             p["title"], p.get("purchase_price_eur"), p.get("purchase_date"),
             _now()))
        property_id = cur.lastrowid
    return get_property(property_id)


def get_property(property_id: int) -> dict | None:
    with _connect() as c:
        row = c.execute("SELECT * FROM properties WHERE id=?", (property_id,)).fetchone()
        if not row:
            return None
        prop = dict(row)
        entries = [dict(r) for r in c.execute(
            "SELECT * FROM ledger WHERE property_id=? ORDER BY date DESC",
            (property_id,))]
    prop["ledger"] = entries
    prop["totals"] = _ledger_totals(entries)
    return prop


def list_properties() -> list[dict]:
    with _connect() as c:
        rows = c.execute("SELECT id FROM properties ORDER BY created_at DESC").fetchall()
    return [get_property(r["id"]) for r in rows]


def add_ledger_entry(property_id: int, entry: dict) -> dict | None:
    if not get_property(property_id):
        return None
    with _connect() as c:
        c.execute(
            "INSERT INTO ledger (property_id, date, kind, description, amount_eur, capex)"
            " VALUES (?,?,?,?,?,?)",
            (property_id, entry["date"], entry["kind"], entry.get("description", ""),
             entry["amount_eur"], 1 if entry.get("capex") else 0))
    return get_property(property_id)


def _ledger_totals(entries: list[dict]) -> dict:
    rent = sum(e["amount_eur"] for e in entries if e["kind"] == "rent")
    expense = sum(-e["amount_eur"] for e in entries if e["kind"] == "expense")
    capex = sum(-e["amount_eur"] for e in entries if e["capex"])
    return {"rent_income": round(rent, 2), "operating_expense": round(expense, 2),
            "capex_basis": round(capex, 2), "net": round(rent - expense, 2)}
