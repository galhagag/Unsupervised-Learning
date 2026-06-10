"""Sicily adapter - immobiliare.it (internal search JSON API).

Uses the JSON endpoint the immobiliare.it frontend calls for search results
(api-next/search-list). Queries Palermo and Catania apartment sales. Fails
soft if blocked or if the schema drifts.
"""

from .common import MAX_RESULTS, fetch_json, to_listing

PORTAL = "immobiliare.it"
CITY = "Sicily"

# idCategoria 1 = residential, idContratto 1 = sale; idComune Palermo/Catania
SEARCH_URLS = [
    "https://www.immobiliare.it/api-next/search-list/listings/"
    "?fkRegione=sic&idProvincia=PA&idCategoria=1&idContratto=1"
    "&criterio=rilevanza&pag=1&paramsCount=0&path=%2F",
    "https://www.immobiliare.it/api-next/search-list/listings/"
    "?fkRegione=sic&idProvincia=CT&idCategoria=1&idContratto=1"
    "&criterio=rilevanza&pag=1&paramsCount=0&path=%2F",
]


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    listings, errors = [], []
    per_url = max(1, max_results // len(SEARCH_URLS))
    for url in SEARCH_URLS:
        try:
            data = fetch_json(url)
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
            continue
        for row in (data.get("results") or [])[: per_url * 2]:
            try:
                re_data = row.get("realEstate") or {}
                props = (re_data.get("properties") or [{}])[0]
                price = (re_data.get("price") or {}).get("value") or 0
                listing = to_listing(
                    portal=PORTAL,
                    portal_id=str(re_data.get("id", "")),
                    city=CITY,
                    title=re_data.get("title", "Apartment in Sicily"),
                    price_eur=float(price),
                    size_m2=_num((props.get("surface") or "").replace("m²", "")),
                    neighborhood=((props.get("location") or {}).get("macrozone")
                                  or (props.get("location") or {}).get("city", "")),
                    overview=props.get("description", ""),
                    url=(row.get("seo") or {}).get("url")
                        or f"https://www.immobiliare.it/annunci/{re_data.get('id')}/",
                )
            except Exception:
                continue
            if listing:
                listings.append(listing)
            if len(listings) >= max_results:
                break
    if listings:
        return listings, f"{PORTAL}: OK, {len(listings)} listings"
    return [], (f"{PORTAL}: no listings ({'; '.join(errors) or 'schema may have changed'})")


def _num(v) -> float | None:
    try:
        return float(str(v).strip().split()[0].replace(",", "."))
    except (TypeError, ValueError, IndexError):
        return None
