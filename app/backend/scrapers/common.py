"""Shared HTTP + schema-mapping helpers for portal scrapers.

The portals (immobiliare.it, homes.bg, spitogatos.gr) all run bot protection
that fingerprints the TLS handshake, so a vanilla httpx/requests client gets
403 even with perfect browser headers. We therefore prefer curl_cffi, which
impersonates Chrome's TLS fingerprint and gets through ordinary Cloudflare/
Akamai-style protection (DataDome on spitogatos may still challenge).

Set SCRAPER_PROXY (e.g. http://user:pass@host:port) to route requests
through a proxy if your IP gets rate-limited.

Scrapers run on demand and fail soft: each adapter returns (listings,
status) and a blocked/changed portal never breaks the app. Scraping may
conflict with portal terms of service; this is built for personal,
low-volume research use. Keep MAX_RESULTS small and do not poll.
"""

import json
import os
import re

try:
    from curl_cffi import requests as curl_requests
    HAVE_CURL_CFFI = True
except ImportError:  # pragma: no cover - exercised only without the dep
    import httpx
    HAVE_CURL_CFFI = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
              "application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}
TIMEOUT = 20.0
MAX_RESULTS = 6
PROXY = os.environ.get("SCRAPER_PROXY")

# Conservative city defaults used when a portal doesn't expose expected rent.
# EUR per m2 per month (long let) and short-let nightly economics.
CITY_ESTIMATES = {
    "Sofia":  {"rent_per_m2": 11.0, "nightly_per_m2": 0.95, "occupancy_pct": 60},
    "Sicily": {"rent_per_m2": 8.5,  "nightly_per_m2": 1.10, "occupancy_pct": 58},
    "Athens": {"rent_per_m2": 12.5, "nightly_per_m2": 1.05, "occupancy_pct": 62},
}
COUNTRY_BY_CITY = {"Sofia": "bulgaria", "Sicily": "italy", "Athens": "greece"}


def _get(url: str, referer: str | None = None, accept_json: bool = False):
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
        headers["Sec-Fetch-Site"] = "same-origin"
    if accept_json:
        headers["Accept"] = "application/json, text/plain, */*"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Sec-Fetch-Mode"] = "cors"
        headers.pop("Upgrade-Insecure-Requests", None)
    if HAVE_CURL_CFFI:
        proxies = {"http": PROXY, "https": PROXY} if PROXY else None
        r = curl_requests.get(url, headers=headers, timeout=TIMEOUT,
                              impersonate="chrome", proxies=proxies,
                              allow_redirects=True)
        r.raise_for_status()
        return r
    with httpx.Client(headers=headers, timeout=TIMEOUT, proxy=PROXY,
                      follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
        return r


def fetch_json(url: str, referer: str | None = None) -> dict:
    r = _get(url, referer=referer, accept_json=True)
    try:
        return r.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"non-JSON response (likely a bot challenge page, "
                         f"{len(r.text)} bytes)") from e


def fetch_html(url: str, referer: str | None = None) -> str:
    return _get(url, referer=referer).text


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
    return {
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


def parse_number(v) -> float | None:
    """Best-effort numeric extraction: '85', '85 m²', '139 000' (space
    thousands separator, used by homes.bg), '1.250,50', '95,5'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"m²|m2|кв\.?\s?м|sq\.?\s?m|sqm", "", str(v), flags=re.I)
    s = s.replace(" ", " ").strip().strip(".,")
    if re.fullmatch(r"\d{1,3}([ .,]\d{3})+", s):   # 139 000 / 139.000 / 152,000
        s = re.sub(r"[ .,]", "", s)
    else:
        s = s.split()[0].strip(".,") if s.split() else ""
        if "," in s and "." in s:                  # 1.250,50 -> 1250.50
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None
