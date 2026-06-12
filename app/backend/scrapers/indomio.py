"""Athens adapter (primary) - indomio.gr.

indomio.gr is immobiliare.it's Greek portal: same platform, same api-next
JSON search endpoint, and crucially NO DataDome (unlike spitogatos.gr).
Queries Athens-centre apartment sales.
"""

from . import api_next
from .common import MAX_RESULTS

PORTAL = "indomio.gr"
CITY = "Athens"
REFERER = "https://www.indomio.gr/en/sale-homes/athens-center/"

# idCategoria 1 = residential, idContratto 1 = sale; Athens municipality
SEARCH_URLS = [
    "https://www.indomio.gr/api-next/search-list/listings/"
    "?idContratto=1&idCategoria=1&idComune=8842&criterio=rilevanza"
    "&pag=1&paramsCount=2&path=%2Fen%2Fsale-homes%2Fathens-center%2F",
    # fallback query keyed on the SEO path only, in case the comune id drifts
    "https://www.indomio.gr/api-next/search-list/listings/"
    "?idContratto=1&idCategoria=1&criterio=rilevanza"
    "&pag=1&paramsCount=1&path=%2Fen%2Fsale-homes%2Fathens-center%2F",
]


def fetch(max_results: int = MAX_RESULTS) -> tuple[list, str]:
    return api_next.fetch_from(SEARCH_URLS, portal=PORTAL, city=CITY,
                               referer=REFERER, max_results=max_results)
