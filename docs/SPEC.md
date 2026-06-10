# Relocation Investment Explorer — Product Spec & Enhancement Proposal

**Version:** 1.0 (as built, June 2026) · **Branch:** `claude/israel-relocation-investment-app-60k8jj` (PR #1)

## Mission

Help an Israeli investor **find the best residential investment listing** in a closed city list
(Sofia, Sicily, Athens) and provide **all relevant information and links to execute the
acquisition and maintain the building over the years** — including the tax consequences of
moving back to Israel mid-hold.

## Primary user profile

Israeli national currently abroad (<6 consecutive years → no returning-resident exemption),
evaluating a 100k–500k EUR residential purchase, planning to move back to Israel during the
holding period. Not a tax professional; needs decision-grade numbers plus the paper trail to
act on them.

---

# Part 1 — Current state (v1.0)

## 1.1 Architecture

| Layer | Stack | Location |
|---|---|---|
| Backend | FastAPI (Python 3.11), serves built frontend | `app/backend/main.py` |
| Engines | Tax/financial, scoring, history | `tax_engine.py`, `scoring.py`, `history.py` |
| Scrapers | curl_cffi (Chrome TLS impersonation), per-city fallback chains | `app/backend/scrapers/` |
| Data | JSON stores + SQLite history DB | `app/backend/data/` |
| Frontend | React 18 + Vite, no router (tab state) | `app/frontend/src/` |
| Tests | pytest: 34 tests (parsers w/ fixtures, scoring, history, API regressions) | `app/backend/tests/` |

## 1.2 Functional surface (4 tabs / 11 endpoints)

**Opportunities** — listings from three sources (curated samples ×9, researched real listings ×6,
live-scraped) filtered by city/source, ranked by after-tax yield / score / gross yield / price.
Per listing: overview, highlights/risks, €/m², score badge with breakdown, long-let vs short-let
financials side by side, 4-scenario tax comparison, exit-CGT estimate, mortgage modelling
(LTV/rate/term → cash-on-cash), original-listing links. Collapsible area guide (14 areas,
verdicts, 1-10 scores, €/m² benchmarks). Listings marked sold/irrelevant are hidden by default.

**History** — SQLite database of every listing ever seen: first/last seen, price, score snapshot,
highlights, status lifecycle (`active → stale/delisted/sold/irrelevant`), auto-delisting on
portal refresh, manual mark/restore. Irrelevant rows retained greyed-out as price history.

**Realtors & Lawyers** — checklist-over-names vetting: universal independence checklist, official
bar/realtor registries per country with links, local red flags, community sources (expat +
Israeli buyer groups), then a sourced starting-point shortlist (no paid placements).

**Israel Tax Guide** — the move-back-to-Israel implications: two rental tax tracks (15% flat
Sec. 122A vs marginal+FTC), returning-resident exemptions and the <6-years case, Amendment 272
reporting, local taxes per country, exit CGT interactions, short-let business-income risk.
Full sourced analysis in `docs/TAX_IMPLICATIONS.md`.

**Endpoints:** `/api/cities`, `/api/scenarios`, `/api/opportunities` (+`/{id}/full-analysis`),
`/api/listings/refresh` + `/live-status`, `/api/areas`, `/api/history` (+`/{id}/status`),
`/api/vetting`, `/api/professionals`.

## 1.3 Engines

**Tax engine** — 4 investor scenarios (abroad / 15% flat / marginal+FTC / returning-resident
gated on years abroad) × 2 rent strategies (long let / short let where legally available,
incl. the central-Athens AMA freeze) × financing (French-annuity; interest deductible on the
marginal track only). Country rules: Bulgaria 10% (effective 9%), Italy cedolare secca 21/26%,
Greece progressive 15–45% (2026 scale); CGT 10% / 26%-then-0%-after-5y / suspended-then-15%;
Israeli 25% CGT with FTC.

**Scoring** — 0–100 composite: location 25% + yield 25% + growth 20% + value-vs-benchmark 15% +
liquidity 15%, minus capped risk adjustment. Scenario-independent (rates the asset).

**History** — relevance tracking with auto-delist on refresh, 30-day staleness, manual closures
that survive re-syncs.

## 1.4 Known limitations (honest list)

- Rent/operating figures on researched & scraped listings are **city-level estimates**.
- Live scraping requires a machine with open internet (sandbox-blocked); portals may still block.
- Single-user, no auth, no persistence beyond the history DB; profile (years abroad, marginal
  rate) is per-session UI state, not saved.
- No FX overlay (EUR only), surtax not computed, no multi-year cash-flow projection — the
  analysis is a snapshot year, not a hold-period model.
- UI verified at the HTTP surface; pixel-level rendering not yet observed in a browser.

---

# Part 2 — Enhancement proposal

## 2.1 Gap analysis against the mission

The investment lifecycle has five stages. v1.0 coverage:

| Stage | What the mission needs | v1.0 coverage |
|---|---|---|
| **Find** | Real listings, fresh, comparable | ✅ Good (3 sources, scores, areas) |
| **Decide** | "Which ONE is best *for me*" | ⚠️ Partial — ranks lists, but no hold-period model, no recommendation, no comparison |
| **Acquire** | Step-by-step path to keys-in-hand with links | ⚠️ Thin — vetting + professionals exist, but no transaction playbook or deal tracking |
| **Operate (years)** | Obligations calendar, costs ledger, documents | ❌ Missing entirely |
| **Exit** | When/how to sell, tax timing | ⚠️ Partial — exit CGT snapshot only, no timing optimisation |

The biggest distance between v1.0 and the stated goal is **right of the buy decision**: the app
currently ends where the real work begins.

## 2.2 Proposed enhancements (phased)

### Phase 1 — Decide: from "ranked list" to "the best listing for you" *(highest value)*

1. **Saved investor profile** (S): years abroad, marginal rate, equity budget, financing intent,
   move-back year, strategy preference — persisted, applied everywhere automatically.
2. **Hold-period projection engine** (M): 10-year cash-flow per listing — rent growth, vacancy,
   capex reserve, appreciation, the *move-back year* switching the tax regime mid-stream,
   Italy's 5-year CGT exemption date, exemption-window expiry; outputs **IRR, NPV, total
   after-tax profit** at exit. This is the number that actually answers "which is best."
3. **Best-pick recommendation** (S): top pick overall + per city = projection IRR blended with
   asset score, with a written "why this one" rationale and "why not the runner-up."
4. **Comparison tray** (M): pin 2–4 listings, side-by-side table of all metrics.
5. **Sensitivity toggles** (S): rent −15%, vacancy 2 months/yr, rate +2pp — does the pick survive?
6. **Investment memo export** (M): one-page PDF/markdown per listing — numbers, score, tax
   treatment, risks, links — the document you'd send to your lawyer/partner.

### Phase 2 — Acquire: the transaction playbook

7. **Acquisition pipeline per country** (M): ordered stages from offer to keys
   (offer → preliminary contract → due diligence → financing → notary/deed → registration →
   utilities & tax registrations), each stage with: required documents (Act 16, compromesso,
   ENFIA certificate, AMA/CIN where relevant), who does it (your lawyer / notary / agent),
   official portal links (land registries, tax authorities), typical cost and duration.
   Data-driven (`acquisition_playbooks.json`), rendered as an interactive checklist.
8. **Deal tracker** (M): start a "deal" from any listing; track stage completion, attach the
   professionals you engaged (from the directory), record actual costs vs estimates; persists
   in SQLite next to history.

### Phase 3 — Operate: the years of ownership

9. **Ownership dashboard** (L): convert a completed deal into a "property"; rent/expense ledger,
   realized yield vs underwritten, occupancy log.
10. **Obligations calendar** (M): auto-generated recurring obligations per country with links —
    IMU (Jun/Dec) and cedolare secca filings for Italy; ENFIA and E2 declarations for Greece;
    Bulgarian municipal property tax; Israeli annual return incl. Amendment 272 foreign-asset
    reporting; insurance renewals, condo fees, safety certificates. Each with due date,
    payment portal link, and done/undone state.
11. **Capex & maintenance log** (S): every improvement recorded — this feeds the CGT cost basis
    at exit, which is money directly recovered.
12. **Alerts** (M): exemption-window expiry, Italy 5-year CGT-free date reached, lease expiry,
    stale obligations, price-drop on watched listings.

### Phase 4 — Intelligence (continuous)

13. **Scheduled refresh + price-drop detection** (S): history DB already stores price; diff on
    re-sight, surface drops as opportunities.
14. **Comparables** (S): price a listing against history-DB comps (€/m² same area).
15. **FX overlay** (S): EUR/ILS on every figure, since the investor thinks in both.

## 2.3 Recommended execution order

**Phase 1 first** — it converts the app from a screener into a decider, which is the core of
the stated goal ("find the best listing"). Items 1–3 (profile, projection engine,
recommendation) are the critical path; 4–6 follow. Phase 2's playbook (#7) is second — it is
pure curated data + checklist UI, high value for modest effort. Phase 3 becomes relevant the
day a deal closes; build #10 (obligations calendar) early anyway since it doubles as a
pre-purchase cost foresight tool. Phase 4 items are small and can ride along anytime.
