"""Shared helpers for portal scrapers.

Scrapers run on demand (POST /api/listings/refresh) and fail soft: each
adapter returns (listings, status) and a blocked/changed portal never breaks
the app - the curated sample data remains available.

Note: scraping may conflict with portal terms of service; this is built for
personal, low-volume research use. Keep MAX_RESULTS small and do not poll.
"""

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 15.0
MAX_RESULTS = 6

# Conservative city defaults used when a portal doesn't expose expected rent.
# EUR per m2 per month (long let) and short-let nightly economics.
CITY_ESTIMATES = {
    "Sofia":  {"rent_per_m2": 11.0, "nightly_per_m2": 0.95, "occupancy_pct": 60},
    "Sicily": {"rent_per_m2": 8.5,  "nightly_per_m2": 1.10, "occupancy_pct": 58},
    "Athens": {"rent_per_m2": 12.5, "nightly_per_m2": 1.05, "occupancy_pct": 62},
}
COUNTRY_BY_CITY = {"Sofia": "bulgaria", "Sicily": "italy", "Athens": "greece"}


def fetch_json(url: str, **kwargs) -> dict:
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as c:
        r = c.get(url, **kwargs)
        r.raise_for_status()
        return r.json()


def fetch_html(url: str, **kwargs) -> str:
    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as c:
        r = c.get(url, **kwargs)
        r.raise_for_status()
        return r.text


def to_listing(*, portal: str, portal_id: str, city: str, title: str,
               price_eur: float, size_m2: float | None, url: str,
               neighborhood: str = "", overview: str = "") -> dict | None:
    """Map a scraped record onto the app's listing schema, estimating the
    rental economics from city-level defaults (flagged as estimates)."""
    if not price_eur or price_eur < 20_000:   # land/parking/garbage rows
        return None
    size = size_m2 or 60
    est = CITY_ESTIMATES[city]
    monthly_rent = round(size * est["rent_per_m2"])
    nightly = round(size * est["nightly_per_m2"])
    listing = {
        "id": f"{portal}-{portal_id}",
        "city": city,
        "country": COUNTRY_BY_CITY[city],
        "title": title.strip()[:120],
        "overview": (overview.strip()[:400] or
                     f"Live listing from {portal}. Rent and costs are "
                     f"city-level ESTIMATES - verify before relying on the "
                     f"analysis."),
        "price_eur": round(price_eur),
        "size_m2": size,
        "expected_monthly_rent_eur": monthly_rent,
        "annual_operating_costs_eur": max(800, round(price_eur * 0.012)),
        "neighborhood": neighborhood.strip()[:80],
        "highlights": [f"Live listing - source: {portal}"],
        "risks": ["Rent/cost figures are city-level estimates, not "
                  "underwritten numbers"],
        "data_source": portal,
        "listing_url": url,
        "estimated": True,
        "short_let": {
            "allowed": True,
            "nightly_rate_eur": nightly,
            "occupancy_pct": est["occupancy_pct"],
            "note": "Estimated short-let economics. For Athens: verify the "
                    "address is OUTSIDE central districts 1-3 (AMA "
                    "registration freeze until end-2026).",
        },
    }
    return listing
