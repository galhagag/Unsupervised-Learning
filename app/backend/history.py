"""Historical listings database (SQLite).

Every listing the app has ever seen - curated, researched, or live-scraped -
is upserted here with its score snapshot and highlights. Relevance tracking:

  active    - present in the current data
  stale     - live/researched listing not re-confirmed for STALE_AFTER_DAYS
  delisted  - live listing that disappeared from a later successful refresh
  sold / irrelevant - set manually via the API

`relevant` is 0 for delisted/sold/irrelevant rows; they stay in the
database for price-history reference but are flagged in the UI.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "history.db"
STALE_AFTER_DAYS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id            TEXT PRIMARY KEY,
    city          TEXT NOT NULL,
    title         TEXT NOT NULL,
    price_eur     INTEGER NOT NULL,
    size_m2       REAL,
    neighborhood  TEXT,
    data_source   TEXT,
    listing_url   TEXT,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    relevant      INTEGER NOT NULL DEFAULT 1,
    status_note   TEXT DEFAULT '',
    highlights    TEXT DEFAULT '[]',
    score_total   REAL,
    score_grade   TEXT,
    score_json    TEXT DEFAULT '{}'
);
"""

MANUAL_STATUSES = {"sold", "irrelevant", "active"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def sync(listings: list[dict], scores: dict[str, dict],
         seen_live_ids: set[str] | None = None,
         refreshed_cities: set[str] | None = None) -> None:
    """Upsert current listings; mark vanished live listings as delisted.

    seen_live_ids/refreshed_cities: after a successful live refresh for a
    city, any live row of that city NOT in seen_live_ids gets delisted.
    """
    today = _today()
    with _connect() as conn:
        for l in listings:
            s = scores.get(l["id"], {})
            row = conn.execute("SELECT id, status FROM listings WHERE id=?",
                               (l["id"],)).fetchone()
            if row:
                # never resurrect manually-closed rows
                if row["status"] in ("sold", "irrelevant"):
                    continue
                conn.execute(
                    "UPDATE listings SET last_seen=?, price_eur=?, status='active',"
                    " relevant=1, highlights=?, score_total=?, score_grade=?,"
                    " score_json=? WHERE id=?",
                    (today, l["price_eur"], json.dumps(l.get("highlights", [])),
                     s.get("total"), s.get("grade"), json.dumps(s), l["id"]))
            else:
                conn.execute(
                    "INSERT INTO listings (id, city, title, price_eur, size_m2,"
                    " neighborhood, data_source, listing_url, first_seen,"
                    " last_seen, status, relevant, highlights, score_total,"
                    " score_grade, score_json)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,'active',1,?,?,?,?)",
                    (l["id"], l["city"], l["title"], l["price_eur"],
                     l.get("size_m2"), l.get("neighborhood", ""),
                     l.get("data_source", ""), l.get("listing_url", ""),
                     today, today, json.dumps(l.get("highlights", [])),
                     s.get("total"), s.get("grade"), json.dumps(s)))

        if seen_live_ids is not None and refreshed_cities:
            placeholders = ",".join("?" * len(refreshed_cities))
            for row in conn.execute(
                    f"SELECT id FROM listings WHERE status='active' AND "
                    f"data_source NOT LIKE '%sample%' AND data_source NOT LIKE "
                    f"'%researched%' AND city IN ({placeholders})",
                    tuple(refreshed_cities)):
                if row["id"] not in seen_live_ids:
                    conn.execute(
                        "UPDATE listings SET status='delisted', relevant=0,"
                        " status_note='disappeared from portal refresh of '||?"
                        " WHERE id=?", (_today(), row["id"]))

        # age-out: live/researched rows unseen for STALE_AFTER_DAYS
        conn.execute(
            "UPDATE listings SET status='stale' WHERE status='active' AND"
            " data_source NOT LIKE '%sample%' AND"
            " julianday('now') - julianday(last_seen) > ?", (STALE_AFTER_DAYS,))


def set_status(listing_id: str, status: str, note: str = "") -> bool:
    if status not in MANUAL_STATUSES:
        raise ValueError(f"status must be one of {sorted(MANUAL_STATUSES)}")
    relevant = 1 if status == "active" else 0
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE listings SET status=?, relevant=?, status_note=? WHERE id=?",
            (status, relevant, note, listing_id))
        return cur.rowcount > 0


def query(city: str | None = None, include_irrelevant: bool = True) -> list[dict]:
    sql = "SELECT * FROM listings"
    where, params = [], []
    if city:
        where.append("city = ?")
        params.append(city)
    if not include_irrelevant:
        where.append("relevant = 1")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY relevant DESC, score_total DESC"
    with _connect() as conn:
        rows = [dict(r) for r in conn.execute(sql, params)]
    for r in rows:
        r["highlights"] = json.loads(r["highlights"] or "[]")
        r["score"] = json.loads(r.pop("score_json") or "{}")
        r["relevant"] = bool(r["relevant"])
    return rows
