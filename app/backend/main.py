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

import scrapers
import tax_engine

DATA_DIR = Path(__file__).parent / "data"
LISTINGS = json.loads((DATA_DIR / "listings.json").read_text())
PROFESSIONALS = json.loads((DATA_DIR / "professionals.json").read_text())
VETTING = json.loads((DATA_DIR / "vetting.json").read_text())
LIVE_FILE = DATA_DIR / "live_listings.json"


def _live() -> dict:
    if LIVE_FILE.exists():
        return json.loads(LIVE_FILE.read_text())
    return {"fetched_at": None, "status": {}, "listings": []}


def _all_listings(source: str) -> list:
    if source == "sample":
        return LISTINGS
    if source == "live":
        return _live()["listings"]
    return LISTINGS + _live()["listings"]

CITIES = ["Sofia", "Sicily", "Athens"]

app = FastAPI(title="Relocation Investment Explorer",
              description="Property opportunities in Sofia, Sicily & Athens "
                          "with Israel-relocation tax modelling.")

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


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
                  source: str = Query("all", pattern="^(all|sample|live)$"),
                  sort: str = Query("after_tax_yield")):
    """Listings ranked by after-tax yield under the chosen tax scenario.

    Returns long-let financials plus a short-let analysis side by side
    (null where short letting is not legally available to a new buyer).
    """
    pool = _all_listings(source)
    items = [l for l in pool if not city or l["city"].lower() == city.lower()]
    if city and not items and not [l for l in pool if l["city"].lower() == city.lower()]:
        raise HTTPException(404, f"Unknown city '{city}'. Choose from {CITIES}.")

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
                        "financials_short_let": short_let})

    key = {
        "after_tax_yield": lambda r: r["financials"]["after_tax_yield_pct"],
        "gross_yield": lambda r: r["financials"]["gross_yield_pct"],
        "price": lambda r: -r["price_eur"],
    }.get(sort)
    if key is None:
        raise HTTPException(400, f"Unknown sort '{sort}'.")
    results.sort(key=key, reverse=True)
    return {"scenario": scenario, "count": len(results), "results": results}


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
    return {"fetched_at": cache["fetched_at"], "status": cache["status"],
            "live_count": len(cache["listings"])}


@app.get("/api/listings/live-status")
def live_status():
    cache = _live()
    return {"fetched_at": cache["fetched_at"], "status": cache["status"],
            "live_count": len(cache["listings"])}


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
