"""Portal scraper registry: ordered fallback chain of adapters per city."""

from . import homes_bg, immobiliare, indomio, spitogatos

ADAPTERS = {
    "Sofia": [homes_bg],
    "Sicily": [immobiliare],
    "Athens": [indomio, spitogatos],   # indomio first: no DataDome
}


def refresh(cities: list[str] | None = None, max_per_city: int = 6) -> dict:
    """Run each city's adapter chain until one yields listings.

    Returns {listings, status} and never raises - every adapter fails soft.
    """
    listings, status = [], {}
    for city, chain in ADAPTERS.items():
        if cities and city not in cities:
            continue
        attempts = []
        for adapter in chain:
            city_listings, city_status = adapter.fetch(max_per_city)
            attempts.append(city_status)
            if city_listings:
                listings.extend(city_listings)
                break
        status[city] = " | ".join(attempts)
    return {"listings": listings, "status": status}
