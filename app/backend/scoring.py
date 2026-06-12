"""Listing scoring engine.

Produces a 0-100 composite score per listing with a transparent breakdown:

  location   (25%)  - area quality from the area guide (data/areas.json)
  yield      (25%)  - net pre-tax long-let yield on all-in cost
  growth     (20%)  - area appreciation outlook
  value      (15%)  - price per m2 vs the area/city benchmark
  liquidity  (15%)  - how fast the asset rents and resells

plus a risk adjustment (capped at -15) for listing-specific risks,
estimated data, and blocked short-let optionality. The score is
scenario-independent: it rates the asset, not the investor's tax position.
"""

import json
from pathlib import Path

import tax_engine

AREAS = json.loads((Path(__file__).parent / "data" / "areas.json").read_text())

WEIGHTS = {"location": 0.25, "yield": 0.25, "growth": 0.20,
           "value": 0.15, "liquidity": 0.15}

CITY_DEFAULTS = {   # fallback when a neighborhood matches no area entry
    "Sofia":  {"scores": {"location": 6, "growth": 6, "liquidity": 7}, "price_eur_m2": 2200},
    "Athens": {"scores": {"location": 6, "growth": 7, "liquidity": 7}, "price_eur_m2": 2600},
    "Sicily": {"scores": {"location": 6, "growth": 6, "liquidity": 6}, "price_eur_m2": 1500},
}

GRADES = [(85, "A"), (78, "A-"), (71, "B+"), (64, "B"), (57, "B-"), (50, "C+"), (0, "C")]


def match_area(listing: dict) -> dict | None:
    """Find the area-guide entry whose aliases appear in the listing's
    neighborhood or title."""
    haystack = f"{listing.get('neighborhood', '')} {listing.get('title', '')}".lower()
    for area in AREAS["areas"]:
        if area["city"] != listing["city"]:
            continue
        if any(alias.lower() in haystack for alias in area["aliases"]):
            return area
    return None


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def score(listing: dict) -> dict:
    area = match_area(listing)
    base = area or CITY_DEFAULTS[listing["city"]]
    rationale = []

    location = base["scores"]["location"] * 10
    growth = base["scores"]["growth"] * 10
    liquidity = base["scores"]["liquidity"] * 10
    if area:
        rationale.append(f"Area: {area['name']} - {area['verdict']}.")
    else:
        rationale.append("Neighborhood not in the area guide - city-default "
                         "location/growth/liquidity scores applied.")

    # Yield: net pre-tax long-let yield on all-in cost. 2% -> 20, 6%+ -> 100.
    fin = tax_engine.analyze(listing, "abroad")
    y = fin["net_pre_tax_yield_pct"]
    yield_score = _clamp((y - 2.0) / 4.0 * 80 + 20, 10, 100)
    rationale.append(f"Net pre-tax yield {y}% on all-in cost.")

    # Value: benchmark EUR/m2 vs asking EUR/m2. At benchmark -> 65;
    # 30% below -> ~92, 30% above -> ~38.
    ppm2 = listing["price_eur"] / listing["size_m2"]
    bench = base["price_eur_m2"]
    value_score = _clamp(65 + (bench / ppm2 - 1) * 90, 10, 100)
    rationale.append(f"Asking EUR {ppm2:,.0f}/m2 vs ~EUR {bench:,}/m2 "
                     f"benchmark for the area.")

    # Risk adjustment.
    adjustment = 0
    risks = listing.get("risks", [])
    if len(risks) > 1:
        adjustment -= 3 * (len(risks) - 1)
    if listing.get("estimated"):
        adjustment -= 5
        rationale.append("Estimated rent/cost data (-5).")
    if not tax_engine.short_let_allowed(listing):
        adjustment -= 5
        rationale.append("No short-let optionality (-5).")
    adjustment = max(-15, adjustment)

    components = {"location": location, "yield": round(yield_score, 1),
                  "growth": growth, "value": round(value_score, 1),
                  "liquidity": liquidity}
    total = sum(components[k] * WEIGHTS[k] for k in WEIGHTS) + adjustment
    total = round(_clamp(total), 1)
    grade = next(g for cutoff, g in GRADES if total >= cutoff)

    return {"total": total, "grade": grade, "components": components,
            "risk_adjustment": adjustment,
            "area": area["name"] if area else None,
            "area_verdict": area["verdict"] if area else None,
            "rationale": rationale}
