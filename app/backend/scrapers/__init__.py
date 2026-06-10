"""Portal scraper registry: one adapter per city in the closed list."""

from . import homes_bg, immobiliare, spitogatos

ADAPTERS = {
    "Sofia": homes_bg,
    "Sicily": immobiliare,
    "Athens": spitogatos,
}


def refresh(cities: list[str] | None = None, max_per_city: int = 6) -> dict:
    """Run the adapters and return {listings, status} - never raises."""
    listings, status = [], {}
    for city, adapter in ADAPTERS.items():
        if cities and city not in cities:
            continue
        city_listings, city_status = adapter.fetch(max_per_city)
        listings.extend(city_listings)
        status[city] = city_status
    return {"listings": listings, "status": status}
