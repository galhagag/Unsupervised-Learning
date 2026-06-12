"""Athens adapter (fallback) - spitogatos.gr (HTML, best effort).

Spitogatos sits behind DataDome bot protection; curl_cffi's Chrome TLS
impersonation gets through some of the time, a JS challenge the rest. This
adapter parses the JSON-LD blocks embedded in the search page when it gets
through and otherwise fails soft. indomio.gr (no DataDome) is the primary
Athens source; this runs only if indomio yields nothing.
"""

import json
import re

from .common import MAX_RESULTS, fetch_html, to_listing

PORTAL = "spitogatos.gr"
CITY = "Athens"

SEARCH_URL = "https://en.spitogatos.gr/for_sale-homes/athens-center"


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    try:
        html = fetch_html(SEARCH_URL, referer="https://en.spitogatos.gr/")
    except Exception as e:
        return [], (f"{PORTAL}: fetch failed ({type(e).__name__}) - DataDome "
                    "challenge likely; retry later or add Athens listings "
                    "manually")
    listings = parse_jsonld(html, max_results)
    if listings:
        return listings, f"{PORTAL}: OK, {len(listings)} listings"
    return [], (f"{PORTAL}: page fetched but no listings parsed - likely a "
                "DataDome challenge page")


def parse_jsonld(html: str, max_results: int) -> list:
    listings = []
    for block in re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.S):
        try:
            data = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        # itemList pages nest products under itemListElement
        for wrapper in list(items):
            for el in wrapper.get("itemListElement", []) if isinstance(wrapper, dict) else []:
                items.append(el.get("item", el))
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") not in ("Product", "Residence", "Apartment",
                                         "SingleFamilyResidence", "Offer"):
                continue
            try:
                offer = item.get("offers") or item
                listing = to_listing(
                    portal=PORTAL,
                    portal_id=str(item.get("sku") or item.get("@id")
                                  or len(listings)),
                    city=CITY,
                    title=item.get("name", "Apartment in Athens"),
                    price_eur=float(offer.get("price") or 0),
                    size_m2=_size_from_text(item.get("name", "") + " " +
                                            item.get("description", "")),
                    overview=item.get("description", ""),
                    url=item.get("url") or SEARCH_URL,
                )
            except Exception:
                continue
            if listing:
                listings.append(listing)
            if len(listings) >= max_results:
                return listings
    return listings


def _size_from_text(text: str) -> float | None:
    m = re.search(r"(\d+)\s*(?:m²|sq\.?\s?m|sqm|τ\.?μ)", text, re.I)
    return float(m.group(1)) if m else None
