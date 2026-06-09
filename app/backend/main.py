"""Relocation Investment Explorer - API.

Serves curated property opportunities in Sofia, Sicily and Athens with
per-scenario financial analysis (including the move-back-to-Israel tax
scenarios), plus vetted realtor/lawyer recommendations per city.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import tax_engine

DATA_DIR = Path(__file__).parent / "data"
LISTINGS = json.loads((DATA_DIR / "listings.json").read_text())
PROFESSIONALS = json.loads((DATA_DIR / "professionals.json").read_text())
VETTING = json.loads((DATA_DIR / "vetting.json").read_text())

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
                  sort: str = Query("after_tax_yield")):
    """Listings ranked by after-tax yield under the chosen tax scenario.

    Returns long-let financials plus a short-let analysis side by side
    (null where short letting is not legally available to a new buyer).
    """
    items = [l for l in LISTINGS if not city or l["city"].lower() == city.lower()]
    if city and not items:
        raise HTTPException(404, f"Unknown city '{city}'. Choose from {CITIES}.")

    results = []
    for listing in items:
        try:
            long_let = tax_engine.analyze(listing, scenario, marginal_rate,
                                          years_abroad=years_abroad)
            short_let = None
            if tax_engine.short_let_allowed(listing):
                short_let = tax_engine.analyze(listing, scenario, marginal_rate,
                                               rent_strategy="short_let",
                                               years_abroad=years_abroad)
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
                  years_abroad: int = Query(5, ge=0, le=40)):
    """All four tax scenarios x both rent strategies for one listing."""
    listing = next((l for l in LISTINGS if l["id"] == listing_id), None)
    if listing is None:
        raise HTTPException(404, f"No listing '{listing_id}'.")
    return {"listing": listing,
            "strategies": tax_engine.analyze_all_scenarios(
                listing, marginal_rate, years_abroad=years_abroad)}


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
