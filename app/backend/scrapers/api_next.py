"""Shared parser for the immobiliare-group 'api-next' search endpoint.

immobiliare.it (Italy) and indomio.gr (Greece) run on the same platform and
expose the same JSON search API that their own frontends call:

    GET <base>/api-next/search-list/listings/?<filters>&pag=1

Response shape (stable since 2023):
    {"count": N, "results": [{"realEstate": {"id", "title",
        "price": {"value", ...},
        "properties": [{"surface": "90 m²",
                        "location": {"city", "macrozone", ...},
                        "description": ...}]},
      "seo": {"url": "https://..."}}, ...]}
"""

from .common import fetch_json, parse_number, to_listing


def parse_results(data: dict, *, portal: str, city: str,
                  max_results: int) -> list:
    listings = []
    for row in data.get("results") or []:
        try:
            re_data = row.get("realEstate") or {}
            props = (re_data.get("properties") or [{}])[0]
            location = props.get("location") or {}
            price = (re_data.get("price") or {}).get("value") or 0
            listing = to_listing(
                portal=portal,
                portal_id=str(re_data.get("id", "")),
                city=city,
                title=re_data.get("title") or props.get("typologyV2", {}).get("name", "Apartment"),
                price_eur=float(price),
                size_m2=parse_number(props.get("surface")),
                neighborhood=location.get("macrozone") or location.get("city") or "",
                overview=str(props.get("description") or ""),
                url=(row.get("seo") or {}).get("url") or "",
            )
        except Exception:
            continue
        if listing and listing["listing_url"]:
            listings.append(listing)
        if len(listings) >= max_results:
            break
    return listings


def fetch_from(search_urls: list[str], *, portal: str, city: str,
               referer: str, max_results: int) -> tuple[list, str]:
    listings, errors = [], []
    per_url = max(1, max_results // len(search_urls))
    for url in search_urls:
        try:
            data = fetch_json(url, referer=referer)
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
            continue
        listings.extend(parse_results(data, portal=portal, city=city,
                                      max_results=per_url))
        if len(listings) >= max_results:
            break
    if listings:
        return listings[:max_results], f"{portal}: OK, {len(listings[:max_results])} listings"
    return [], f"{portal}: no listings ({'; '.join(errors) or 'schema may have changed'})"
