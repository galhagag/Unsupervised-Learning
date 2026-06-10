# Relocation Investment Explorer

Full-stack app for evaluating residential investment opportunities in **Sofia, Sicily and
Athens**, with per-listing financial analysis under four tax scenarios — including the
**move-back-to-Israel** scenario (Sec. 122A 15% track, marginal-rate track with foreign tax
credit, and the returning-resident exemption window).

See [`../docs/TAX_IMPLICATIONS.md`](../docs/TAX_IMPLICATIONS.md) for the full tax analysis
with sources.

## Stack

- **Backend** — FastAPI (`app/backend`): listings + professionals data, financial/tax engine
- **Frontend** — React + Vite (`app/frontend`): Opportunities, Realtors & Lawyers, Israel Tax Guide tabs

## Run

```bash
# Backend (port 8000)
cd app/backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend dev server (port 5173, proxies /api to 8000)
cd app/frontend
npm install
npm run dev
```

Production: `npm run build` in `frontend/`, then the backend serves `frontend/dist` at `/`.

## API

| Endpoint | Description |
|---|---|
| `GET /api/cities` | The closed city list |
| `GET /api/scenarios` | The four tax scenarios |
| `GET /api/opportunities?city=&scenario=&marginal_rate=&years_abroad=&ltv=&mortgage_rate=&mortgage_term_years=&source=&sort=` | Listings ranked by after-tax yield; long-let and short-let financials side by side |
| `GET /api/opportunities/{id}/full-analysis` | One listing, all scenarios × both rent strategies |
| `POST /api/listings/refresh?city=` | Scrape the portals and cache live listings (fails soft per portal) |
| `GET /api/listings/live-status` | Last fetch time and per-portal status |
| `GET /api/professionals?city=&type=` | Realtor / lawyer shortlist with selection methodology |
| `GET /api/vetting` | Vetting checklists, official registries, community sources |

## Financing

Pass `ltv` (0–0.8), `mortgage_rate` and `mortgage_term_years` to model a French-annuity
mortgage: the response adds equity invested, annual debt service, after-tax cash flow after
debt, and cash-on-cash return. Year-1 interest is deducted on the Israeli marginal track
only (not on the 15% flat track, and it never reduces the local gross-based taxes).

## Data sources

- **Curated listings** (`backend/data/listings.json`): realistic mid-2026 sample data.
- **Live listings** (`POST /api/listings/refresh`): scraper adapters in `backend/scrapers/`
  for homes.bg (Sofia), immobiliare.it (Sicily) and spitogatos.gr (Athens). Each adapter
  fails soft and reports status — spitogatos in particular sits behind DataDome and will
  often require manual entry. Scraped listings carry `estimated: true` because rent and
  operating costs are city-level estimates, not underwritten numbers. Note that scraping
  may conflict with portal terms of service; the adapters are built for personal,
  low-volume research use. **Live fetches will not work from inside a sandboxed
  environment that blocks outbound HTTP — run the backend on your own machine.**
- **Professionals** (`backend/data/professionals.json`) and **vetting toolkit**
  (`backend/data/vetting.json`): compiled from public non-sponsored sources.
