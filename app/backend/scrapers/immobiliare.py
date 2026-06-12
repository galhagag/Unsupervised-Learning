"""Sicily adapter - immobiliare.it (internal search JSON API).

Queries Palermo and Catania apartment sales through the api-next endpoint
the site's own frontend uses. Requires browser TLS impersonation
(curl_cffi) to get past the edge bot check.
"""

from . import api_next
from .common import MAX_RESULTS

PORTAL = "immobiliare.it"
CITY = "Sicily"
REFERER = "https://www.immobiliare.it/vendita-case/palermo/"

# idCategoria 1 = residential, idContratto 1 = sale
SEARCH_URLS = [
    "https://www.immobiliare.it/api-next/search-list/listings/"
    "?idContratto=1&idCategoria=1&idProvincia=PA&criterio=rilevanza"
    "&pag=1&paramsCount=2&path=%2Fvendita-case%2Fpalermo%2F",
    "https://www.immobiliare.it/api-next/search-list/listings/"
    "?idContratto=1&idCategoria=1&idProvincia=CT&criterio=rilevanza"
    "&pag=1&paramsCount=2&path=%2Fvendita-case%2Fcatania%2F",
]


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    return api_next.fetch_from(SEARCH_URLS, portal=PORTAL, city=CITY,
                               referer=REFERER, max_results=max_results)
