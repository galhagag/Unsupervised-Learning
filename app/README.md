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
| `GET /api/opportunities?city=&scenario=&marginal_rate=&sort=` | Listings ranked by after-tax yield under the chosen scenario |
| `GET /api/opportunities/{id}/full-analysis` | One listing, all four scenarios side by side |
| `GET /api/professionals?city=&type=` | Realtor / lawyer shortlist with selection methodology |

## Data status

Listings are **curated sample data** (`backend/data/listings.json`) with realistic mid-2026
prices and rents — they demonstrate the analysis engine, not live inventory. Professionals
(`backend/data/professionals.json`) are compiled from public non-sponsored sources with the
selection methodology stated in the payload. Wiring to live listing sources is an open
design decision.
