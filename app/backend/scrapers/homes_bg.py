"""Sofia adapter - homes.bg (JSON API).

homes.bg exposes the JSON endpoint its own frontend uses; this is the most
scrape-friendly of the Bulgarian portals (imot.bg obfuscates URLs and blocks
bots aggressively). Selectors verified June 2026 - if the schema drifts, the
adapter fails soft with a status message.
"""

from .common import MAX_RESULTS, fetch_json, to_listing

PORTAL = "homes.bg"
CITY = "Sofia"

# typeId 1 = apartment sales; locationId 1 = Sofia city
SEARCH_URL = ("https://www.homes.bg/api/offers?currencyId=1&filterOrderBy=0"
              "&locationId=1&typeId=ApartmentSell&page=1")

EUR_PER_BGN = 1 / 1.95583  # fixed peg carried into euro adoption


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    try:
        data = fetch_json(SEARCH_URL)
    except Exception as e:
        return [], f"{PORTAL}: fetch failed ({type(e).__name__}: {e})"

    listings = []
    for row in (data.get("result") or data.get("offers") or [])[: max_results * 2]:
        try:
            price = row.get("price") or {}
            value = float(price.get("value") or 0)
            if (price.get("currency") or "").upper() in ("BGN", "ЛВ."):
                value *= EUR_PER_BGN
            listing = to_listing(
                portal=PORTAL,
                portal_id=str(row.get("id", "")),
                city=CITY,
                title=row.get("title") or row.get("type", "Apartment in Sofia"),
                price_eur=value,
                size_m2=_num(row.get("area")),
                neighborhood=(row.get("location") or {}).get("description", "")
                             if isinstance(row.get("location"), dict)
                             else str(row.get("location") or ""),
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


def _num(v) -> float | None:
    try:
        return float(str(v).split()[0])
    except (TypeError, ValueError, IndexError):
        return None
