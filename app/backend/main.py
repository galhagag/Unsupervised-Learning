"""Relocation Investment Explorer - API.

Serves curated property opportunities in Sofia, Sicily and Athens with
per-scenario financial analysis (including the move-back-to-Israel tax
scenarios), plus vetted realtor/lawyer recommendations per city.
"""

import json
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import history
import scoring
import scrapers
import tax_engine

DATA_DIR = Path(__file__).parent / "data"
LISTINGS = json.loads((DATA_DIR / "listings.json").read_text())
PROFESSIONALS = json.loads((DATA_DIR / "professionals.json").read_text())
VETTING = json.loads((DATA_DIR / "vetting.json").read_text())
RESEARCHED = json.loads((DATA_DIR / "researched_listings.json").read_text())
AREAS = json.loads((DATA_DIR / "areas.json").read_text())
LIVE_FILE = DATA_DIR / "live_listings.json"


def _live() -> dict:
    if LIVE_FILE.exists():
        return json.loads(LIVE_FILE.read_text())
    return {"fetched_at": None, "status": {}, "listings": []}


def _all_listings(source: str) -> list:
    pools = {
        "sample": LISTINGS,
        "researched": RESEARCHED,
        "live": _live()["listings"],
    }
    if source in pools:        # empty pool is a valid answer, not a fallthrough
        return pools[source]
    return LISTINGS + RESEARCHED + _live()["listings"]

CITIES = ["Sofia", "Sicily", "Athens"]

app = FastAPI(title="Relocation Investment Explorer",
              description="Property opportunities in Sofia, Sicily & Athens "
                          "with Israel-relocation tax modelling.")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Sample closed entries so the history view demonstrates relevance tracking.
HISTORICAL_EXAMPLES = [
    {"id": "hist-sof-001", "city": "Sofia", "country": "bulgaria",
     "title": "2-bed in Iztok, 71 m2 (example of a sold listing)",
     "price_eur": 168000, "size_m2": 71, "neighborhood": "Iztok",
     "expected_monthly_rent_eur": 800, "annual_operating_costs_eur": 1400,
     "highlights": ["Sold within 3 weeks at asking - Iztok liquidity datapoint"],
     "risks": [], "data_source": "sample (historical)",
     "_status": ("sold", "Example: sold May 2026 at asking price.")},
    {"id": "hist-ath-001", "city": "Athens", "country": "greece",
     "title": "1-bed in Pagrati, 48 m2 (example of a delisted listing)",
     "price_eur": 142000, "size_m2": 48, "neighborhood": "Pagrati",
     "expected_monthly_rent_eur": 620, "annual_operating_costs_eur": 1500,
     "highlights": ["Withdrawn after two weeks - typical for well-priced Pagrati stock"],
     "risks": [], "data_source": "sample (historical)",
     "_status": ("irrelevant", "Example: withdrawn by owner, April 2026.")},
    {"id": "hist-sic-001", "city": "Sicily", "country": "italy",
     "title": "2-bed near Teatro Massimo, Palermo, 75 m2 (example, sold)",
     "price_eur": 119000, "size_m2": 75, "neighborhood": "Palermo - Centro Storico",
     "expected_monthly_rent_eur": 620, "annual_operating_costs_eur": 1500,
     "highlights": ["Sold ~6% under asking - Centro Storico negotiation datapoint"],
     "risks": [], "data_source": "sample (historical)",
     "_status": ("sold", "Example: closed June 2026, 6% below asking.")},
]


@app.on_event("startup")
def sync_history() -> None:
    current = LISTINGS + RESEARCHED + _live()["listings"]
    scores = {l["id"]: scoring.score(l) for l in current}
    history.sync(current, scores)
    examples = [dict(e) for e in HISTORICAL_EXAMPLES]
    statuses = {e["id"]: e.pop("_status") for e in examples}
    history.sync(examples, {e["id"]: scoring.score(e) for e in examples})
    for eid, (status, note) in statuses.items():
        history.set_status(eid, status, note)


@app.get("/api/cities")
def cities():
    return CITIES


@app.get("/api/scenarios")
def scenarios():
    return [{"id": k, **v} for k, v in tax_engine.SCENARIOS.items()]


@app.get("/api/opportunities")
def opportunities(city: str | None = Query(None),
                  scenario: str = Query("abroad"),
                  marginal_rate: float = Query(0.47, ge=0.10, le=0.50),
                  years_abroad: int = Query(5, ge=0, le=40),
                  ltv: float = Query(0.0, ge=0.0, le=0.8),
                  mortgage_rate: float = Query(0.045, ge=0.005, le=0.15),
                  mortgage_term_years: int = Query(20, ge=5, le=35),
                  source: str = Query("all", pattern="^(all|sample|researched|live)$"),
                  include_closed: bool = Query(False),
                  sort: str = Query("after_tax_yield")):
    """Listings ranked by after-tax yield under the chosen tax scenario.

    Returns long-let financials plus a short-let analysis side by side
    (null where short letting is not legally available to a new buyer).
    Listings marked sold/irrelevant/delisted in the history database are
    excluded unless include_closed=true.
    """
    if city and city.lower() not in {c.lower() for c in CITIES}:
        raise HTTPException(404, f"Unknown city '{city}'. Choose from {CITIES}.")
    pool = _all_listings(source)
    items = [l for l in pool if not city or l["city"].lower() == city.lower()]
    closed = history.closed_ids()
    closed_excluded = 0
    if not include_closed:
        closed_excluded = sum(1 for l in items if l["id"] in closed)
        items = [l for l in items if l["id"] not in closed]

    fin_kwargs = dict(marginal_rate=marginal_rate, years_abroad=years_abroad,
                      ltv=ltv, mortgage_rate=mortgage_rate,
                      mortgage_term_years=mortgage_term_years)
    results = []
    for listing in items:
        try:
            long_let = tax_engine.analyze(listing, scenario, **fin_kwargs)
            short_let = None
            if tax_engine.short_let_allowed(listing):
                short_let = tax_engine.analyze(listing, scenario,
                                               rent_strategy="short_let",
                                               **fin_kwargs)
        except ValueError as e:
            raise HTTPException(400, str(e))
        results.append({**listing, "financials": long_let,
                        "financials_short_let": short_let,
                        "score": scoring.score(listing)})

    key = {
        "after_tax_yield": lambda r: r["financials"]["after_tax_yield_pct"],
        "gross_yield": lambda r: r["financials"]["gross_yield_pct"],
        "score": lambda r: r["score"]["total"],
        "price": lambda r: -r["price_eur"],
    }.get(sort)
    if key is None:
        raise HTTPException(400, f"Unknown sort '{sort}'.")
    results.sort(key=key, reverse=True)
    return {"scenario": scenario, "count": len(results),
            "closed_excluded": closed_excluded, "results": results}


@app.get("/api/opportunities/{listing_id}/full-analysis")
def full_analysis(listing_id: str,
                  marginal_rate: float = Query(0.47, ge=0.10, le=0.50),
                  years_abroad: int = Query(5, ge=0, le=40),
                  ltv: float = Query(0.0, ge=0.0, le=0.8),
                  mortgage_rate: float = Query(0.045, ge=0.005, le=0.15),
                  mortgage_term_years: int = Query(20, ge=5, le=35)):
    """All four tax scenarios x both rent strategies for one listing."""
    listing = next((l for l in _all_listings("all") if l["id"] == listing_id), None)
    if listing is None:
        raise HTTPException(404, f"No listing '{listing_id}'.")
    return {"listing": listing,
            "strategies": tax_engine.analyze_all_scenarios(
                listing, marginal_rate, years_abroad=years_abroad, ltv=ltv,
                mortgage_rate=mortgage_rate,
                mortgage_term_years=mortgage_term_years)}


@app.post("/api/listings/refresh")
def refresh_listings(city: str | None = Query(None)):
    """Scrape the portals (homes.bg, immobiliare.it, spitogatos.gr) and cache
    the results. Fails soft per portal - check the returned status map."""
    result = scrapers.refresh([city] if city else None)
    cache = _live()
    if city:  # merge: replace only the refreshed city's listings
        kept = [l for l in cache["listings"] if l["city"] != city]
        cache["listings"] = kept + result["listings"]
        cache["status"] = {**cache.get("status", {}), **result["status"]}
    else:
        cache = {"listings": result["listings"], "status": result["status"]}
    cache["fetched_at"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    LIVE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

    # Record in the history DB; delist live rows that vanished from a
    # successfully refreshed city.
    refreshed = {c for c, s in result["status"].items() if "OK" in s}
    scores = {l["id"]: scoring.score(l) for l in result["listings"]}
    history.sync(result["listings"], scores,
                 seen_live_ids={l["id"] for l in cache["listings"]},
                 refreshed_cities=refreshed)
    return {"fetched_at": cache["fetched_at"], "status": cache["status"],
            "live_count": len(cache["listings"])}


@app.get("/api/listings/live-status")
def live_status():
    cache = _live()
    return {"fetched_at": cache["fetched_at"], "status": cache["status"],
            "live_count": len(cache["listings"])}


@app.get("/api/areas")
def areas(city: str | None = Query(None)):
    """Recommended areas per city with verdicts, scores and benchmarks."""
    items = AREAS["areas"]
    if city:
        items = [a for a in items if a["city"].lower() == city.lower()]
    return {"as_of": AREAS["as_of"], "note": AREAS["note"], "results": items}


@app.get("/api/history")
def listing_history(city: str | None = Query(None),
                    include_irrelevant: bool = Query(True)):
    """Historical listings database with relevance status and score snapshots."""
    rows = history.query(city, include_irrelevant)
    return {"count": len(rows),
            "irrelevant_count": sum(1 for r in rows if not r["relevant"]),
            "results": rows}


@app.post("/api/history/{listing_id}/status")
def set_history_status(listing_id: str,
                       status: str = Query(pattern="^(sold|irrelevant|active)$"),
                       note: str = Query("")):
    """Manually mark a historical listing sold/irrelevant (or re-activate)."""
    if not history.set_status(listing_id, status, note):
        raise HTTPException(404, f"No listing '{listing_id}' in history.")
    return {"id": listing_id, "status": status, "note": note}


@app.get("/api/vetting")
def vetting():
    """Per-country vetting toolkit: checklists, registries, community sources."""
    return VETTING


@app.get("/api/professionals")
def professionals(city: str | None = Query(None),
                  type: str | None = Query(None)):
    items = PROFESSIONALS["professionals"]
    if city:
        items = [p for p in items if p["city"].lower() == city.lower()]
    if type:
        items = [p for p in items if p["type"] == type]
    return {"methodology": PROFESSIONALS["methodology"],
            "disclaimer": PROFESSIONALS["disclaimer"],
            "count": len(items),
            "results": items}


# Serve the built frontend when present (production mode).
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="app")
