"""Sofia adapter - homes.bg (JSON API).

homes.bg exposes the JSON endpoint its own frontend uses; this is the most
scrape-friendly of the Bulgarian portals (imot.bg obfuscates URLs and blocks
bots aggressively). Requires browser TLS impersonation (curl_cffi) to get
past the edge bot check. If the schema drifts, the adapter fails soft with
a status message.

Response shape: {"result": [{"id", "title"/"type", "area",
                  "location": str | {"description": ...},
                  "price": {"value", "currency"}}, ...]}
"""

from .common import MAX_RESULTS, fetch_json, parse_number, to_listing

PORTAL = "homes.bg"
CITY = "Sofia"
REFERER = "https://www.homes.bg/obiavi-prodazhbi-apartamenti/sofia"

# typeId ApartmentSell; locationId 1 = Sofia city
SEARCH_URL = ("https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0"
              "&locationId=1&typeId=ApartmentSell&page=1")

EUR_PER_BGN = 1 / 1.95583  # fixed peg carried into euro adoption


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    try:
        data = fetch_json(SEARCH_URL, referer=REFERER)
    except Exception as e:
        return [], f"{PORTAL}: fetch failed ({type(e).__name__}: {e})"

    listings = []
    for row in (data.get("result") or data.get("offers") or []):
        try:
            price = row.get("price") or {}
            value = parse_number(price.get("value")) or 0
            currency = str(price.get("currency") or "").upper()
            if currency in ("BGN", "ЛВ.", "ЛВ"):
                value *= EUR_PER_BGN
            location = row.get("location")
            neighborhood = (location.get("description", "")
                            if isinstance(location, dict)
                            else str(location or ""))
            listing = to_listing(
                portal=PORTAL,
                portal_id=str(row.get("id", "")),
                city=CITY,
                title=row.get("title") or row.get("type", "Apartment in Sofia"),
                price_eur=value,
                size_m2=parse_number(row.get("area")),
                neighborhood=neighborhood,
                url=f"https://www.homes.bg/offer/{row.get('id')}",
            )
        except Exception:
            continue
        if listing:
            listings.append(listing)
        if len(listings) >= max_results:
            break
    status = (f"{PORTAL}: OK, {len(listings)} listings" if listings
              else f"{PORTAL}: reachable but no rows parsed - schema may have changed")
    return listings, status
