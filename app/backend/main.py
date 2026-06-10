"""Relocation Investment Explorer - API.

Serves curated property opportunities in Sofia, Sicily and Athens with
per-scenario financial analysis (including the move-back-to-Israel tax
scenarios), plus vetted realtor/lawyer recommendations per city.
"""

import json
import time
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import history
import insights
import projection
import recommend
import scoring
import scrapers
import store
import tax_engine

DATA_DIR = Path(__file__).parent / "data"
LISTINGS = json.loads((DATA_DIR / "listings.json").read_text())
PROFESSIONALS = json.loads((DATA_DIR / "professionals.json").read_text())
VETTING = json.loads((DATA_DIR / "vetting.json").read_text())
RESEARCHED = json.loads((DATA_DIR / "researched_listings.json").read_text())
AREAS = json.loads((DATA_DIR / "areas.json").read_text())
PLAYBOOKS = json.loads((DATA_DIR / "acquisition_playbooks.json").read_text())
OBLIGATIONS = json.loads((DATA_DIR / "obligations.json").read_text())
LIVE_FILE = DATA_DIR / "live_listings.json"


def _listing_by_id(listing_id: str) -> dict | None:
    return next((l for l in _all_listings("all") if l["id"] == listing_id), None)


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


# ---- Phase 1: profile, projection, recommendation, comparison ------------

@app.get("/api/profile")
def get_profile():
    return store.get_profile()


@app.put("/api/profile")
def put_profile(patch: dict = Body(...)):
    return store.save_profile(patch)


def _assumptions_from_profile(listing: dict, overrides: dict | None = None) -> projection.ProfileAssumptions:
    prof = {**store.get_profile(), **(overrides or {})}
    return recommend._profile_to_assumptions(prof, listing)


@app.get("/api/opportunities/{listing_id}/projection")
def listing_projection(listing_id: str,
                       rent_pct: float | None = Query(None),
                       vacancy_extra_months: float | None = Query(None),
                       rate_bump_pp: float | None = Query(None)):
    """10-year hold-period projection (IRR/NPV/profit) using the saved
    profile, with optional sensitivity stresses."""
    listing = _listing_by_id(listing_id)
    if not listing:
        raise HTTPException(404, f"No listing '{listing_id}'.")
    prof = store.get_profile()
    # Sensitivity stresses (Phase 1 #5).
    if rent_pct is not None:
        prof["rent_strategy"] = prof.get("rent_strategy", "long_let")
    overrides = {}
    if vacancy_extra_months is not None:
        overrides["vacancy_pct"] = prof.get("vacancy_pct", 5.0) + vacancy_extra_months / 12 * 100
    if rate_bump_pp is not None and prof.get("ltv", 0):
        overrides["mortgage_rate"] = prof.get("mortgage_rate", 0.045) + rate_bump_pp / 100
    assumptions = recommend._profile_to_assumptions({**prof, **overrides}, listing)
    if rent_pct is not None:
        # Apply a rent haircut by scaling the listing's base rent.
        listing = dict(listing,
                       expected_monthly_rent_eur=listing["expected_monthly_rent_eur"] * (1 + rent_pct / 100))
        if listing.get("short_let", {}).get("allowed"):
            sl = dict(listing["short_let"])
            sl["nightly_rate_eur"] = sl["nightly_rate_eur"] * (1 + rent_pct / 100)
            listing["short_let"] = sl
    return projection.project(listing, assumptions)


@app.get("/api/recommendation")
def recommendation(city: str | None = Query(None),
                   source: str = Query("all", pattern="^(all|sample|researched|live)$")):
    """Best-pick recommendation across the pool using the saved profile."""
    closed = history.closed_ids()
    pool = [l for l in _all_listings(source) if l["id"] not in closed
            and (not city or l["city"].lower() == city.lower())]
    return recommend.recommend(pool, store.get_profile())


@app.post("/api/compare")
def compare(ids: list[str] = Body(..., embed=True)):
    """Side-by-side metrics for 2-4 pinned listings."""
    prof = store.get_profile()
    out = []
    for lid in ids[:4]:
        listing = _listing_by_id(lid)
        if not listing:
            continue
        proj = projection.project(listing, recommend._profile_to_assumptions(prof, listing))
        out.append({"listing": listing, "score": scoring.score(listing),
                    "projection": proj,
                    "comparables": insights.comparables(listing, _all_listings("all"))})
    return {"count": len(out), "results": out}


@app.get("/api/opportunities/{listing_id}/memo")
def investment_memo(listing_id: str):
    """One-page investment memo (markdown) for a listing."""
    listing = _listing_by_id(listing_id)
    if not listing:
        raise HTTPException(404, f"No listing '{listing_id}'.")
    prof = store.get_profile()
    proj = projection.project(listing, recommend._profile_to_assumptions(prof, listing))
    sc = scoring.score(listing)
    comps = insights.comparables(listing, _all_listings("all"))
    return {"listing_id": listing_id,
            "markdown": _render_memo(listing, sc, proj, comps, prof)}


def _render_memo(listing, sc, proj, comps, prof) -> str:
    m = proj["metrics"]
    eur = lambda n: f"EUR {n:,}" if n is not None else "n/a"
    lines = [
        f"# Investment memo — {listing['title']}",
        f"\n**{listing['city']} · {eur(listing['price_eur'])} · "
        f"{listing.get('size_m2','?')} m² · {eur(round(listing['price_eur']/listing['size_m2']))}/m²**",
        f"\nScore **{sc['grade']} ({sc['total']}/100)** · Area: {sc['area'] or 'n/a'}"
        f" — {sc['area_verdict'] or ''}",
        f"\n## Overview\n{listing['overview']}",
        "\n## Hold-period projection ({}y, move-back year {})".format(
            prof.get("hold_years", 10), prof.get("move_back_year", "—")),
        f"- IRR: **{m['irr_pct']}%** · NPV: {eur(m['npv'])} · Equity multiple: {m['equity_multiple']}",
        f"- Total after-tax profit: **{eur(m['total_after_tax_profit'])}** on {eur(proj['equity_invested'])} equity",
        f"- Avg annual cash flow: {eur(m['avg_annual_cash_flow'])}",
        f"- Exit: sale {eur(proj['exit']['sale_value'])}, local CGT {eur(proj['exit']['local_cgt'])}, "
        f"Israeli CGT {eur(proj['exit']['israeli_cgt'])}, net {eur(proj['exit']['net_sale_proceeds'])}",
        f"\n## Market position\n- {comps.get('verdict','n/a')} at {eur(comps.get('target_eur_m2'))}/m² "
        f"(area median {eur(comps.get('median_eur_m2'))}/m², {comps.get('peer_count',0)} comps)",
        "\n## Milestones\n" + "\n".join(f"- {ms}" for ms in proj["milestones"]),
        "\n## Highlights\n" + "\n".join(f"- {h}" for h in listing.get("highlights", [])),
        "\n## Risks\n" + "\n".join(f"- {r}" for r in listing.get("risks", [])),
    ]
    if listing.get("listing_url"):
        lines.append(f"\n[Original listing]({listing['listing_url']})")
    lines.append("\n---\n*Decision-support modelling, not investment or tax "
                 "advice. Confirm with your lawyer and an Israeli CPA.*")
    return "\n".join(lines)


# ---- Phase 2: acquisition playbooks & deal tracker -----------------------

@app.get("/api/playbooks/{country}")
def playbook(country: str):
    pb = PLAYBOOKS["countries"].get(country.lower())
    if not pb:
        raise HTTPException(404, f"No playbook for '{country}'. "
                            f"Have: {list(PLAYBOOKS['countries'])}.")
    return {"disclaimer": PLAYBOOKS["disclaimer"], **pb}


@app.get("/api/deals")
def deals():
    return {"results": store.list_deals()}


@app.post("/api/deals")
def create_deal(listing_id: str = Body(..., embed=True)):
    listing = _listing_by_id(listing_id)
    if not listing:
        raise HTTPException(404, f"No listing '{listing_id}'.")
    return store.create_deal(listing)


@app.get("/api/deals/{deal_id}")
def deal(deal_id: int):
    d = store.get_deal(deal_id)
    if not d:
        raise HTTPException(404, f"No deal {deal_id}.")
    d["playbook"] = PLAYBOOKS["countries"].get(d["country"], {})
    return d


@app.put("/api/deals/{deal_id}/stages/{stage_key}")
def update_stage(deal_id: int, stage_key: str, patch: dict = Body(...)):
    d = store.update_deal_stage(deal_id, stage_key, patch.get("done"),
                                patch.get("note"), patch.get("cost_eur"))
    if not d:
        raise HTTPException(404, f"No deal {deal_id}.")
    return d


@app.put("/api/deals/{deal_id}/status")
def deal_status(deal_id: int, status: str = Query(pattern="^(active|completed|abandoned)$")):
    d = store.set_deal_status(deal_id, status)
    if not d:
        raise HTTPException(404, f"No deal {deal_id}.")
    return d


# ---- Phase 3: ownership, obligations, ledger, alerts ---------------------

@app.get("/api/properties")
def properties():
    return {"results": store.list_properties()}


@app.post("/api/properties")
def create_property(body: dict = Body(...)):
    return store.create_property(body)


@app.get("/api/properties/{property_id}")
def property_detail(property_id: int):
    p = store.get_property(property_id)
    if not p:
        raise HTTPException(404, f"No property {property_id}.")
    p["obligations"] = OBLIGATIONS["countries"].get(p["country"], {})
    p["israel_obligations"] = OBLIGATIONS["israel_resident"]
    return p


@app.post("/api/properties/{property_id}/ledger")
def add_ledger(property_id: int, entry: dict = Body(...)):
    p = store.add_ledger_entry(property_id, entry)
    if not p:
        raise HTTPException(404, f"No property {property_id}.")
    return p


@app.get("/api/obligations/{country}")
def obligations(country: str):
    c = OBLIGATIONS["countries"].get(country.lower())
    if not c:
        raise HTTPException(404, f"No obligations for '{country}'.")
    return {"disclaimer": OBLIGATIONS["disclaimer"], **c,
            "israel_resident": OBLIGATIONS["israel_resident"]}


@app.get("/api/alerts")
def alerts():
    return {"results": insights.ownership_alerts(
        store.list_properties(), store.get_profile(), OBLIGATIONS)}


# ---- Phase 4: market intelligence ----------------------------------------

@app.get("/api/fx")
def fx():
    return {"eur_ils": insights.EUR_ILS, "as_of": insights.EUR_ILS_AS_OF}


@app.get("/api/price-changes")
def price_changes():
    return {"results": insights.price_changes()}


# Serve the built frontend when present (production mode).
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="app")
