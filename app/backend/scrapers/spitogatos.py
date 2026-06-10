"""Athens adapter - spitogatos.gr (HTML, best effort).

Spitogatos sits behind DataDome bot protection, so plain HTTP requests are
frequently challenged. This adapter parses the embedded __NUXT__/JSON-LD data
from the search page when it gets through, and otherwise fails soft with a
clear status so the UI can tell you Athens needs manual entry that day.
"""

import json
import re

from .common import MAX_RESULTS, fetch_html, to_listing

PORTAL = "spitogatos.gr"
CITY = "Athens"

SEARCH_URL = "https://en.spitogatos.gr/for_sale-homes/athens-center"


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    try:
        html = fetch_html(SEARCH_URL)
    except Exception as e:
        return [], (f"{PORTAL}: fetch failed ({type(e).__name__}) - the portal "
                    "uses DataDome bot protection; add Athens listings "
                    "manually or retry later")

    listings = []
    # JSON-LD product blocks are the most stable extraction point.
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                            html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") not in ("Product", "Residence", "Apartment"):
                continue
            try:
                offer = item.get("offers") or {}
                listing = to_listing(
                    portal=PORTAL,
                    portal_id=str(item.get("sku") or item.get("@id") or len(listings)),
                    city=CITY,
                    title=item.get("name", "Apartment in Athens"),
                    price_eur=float(offer.get("price") or 0),
                    size_m2=_size_from_name(item.get("name", "")),
                    overview=item.get("description", ""),
                    url=item.get("url") or SEARCH_URL,
                )
            except Exception:
                continue
            if listing:
                listings.append(listing)
            if len(listings) >= max_results:
                break
    if listings:
        return listings, f"{PORTAL}: OK, {len(listings)} listings"
    return [], (f"{PORTAL}: page fetched but no listings parsed - likely a "
                "DataDome challenge page; add Athens listings manually")


def _size_from_name(name: str) -> float | None:
    m = re.search(r"(\d+)\s*(?:m²|sqm|sq\.m)", name, re.I)
    return float(m.group(1)) if m else None
