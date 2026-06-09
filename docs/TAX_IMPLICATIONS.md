# Tax Implications: Moving Back to Israel While Holding Property in Sofia, Sicily or Athens

*Figures current as of June 2026. Decision-support modelling, not tax advice — confirm with an Israeli CPA before acting.*

## 1. What changes the moment you become an Israeli tax resident again

While you live abroad as a **non-Israeli tax resident**, Israel has no claim on your foreign
rental income or capital gains — only Bulgaria/Italy/Greece tax you. Once you re-establish
Israeli residency (183-day test or "centre of life" test), Israel taxes your **worldwide income**.

Israel's treaties with Bulgaria, Italy and Greece all follow the OECD pattern for immovable
property: **the country where the property sits taxes first**, and Israel taxes on top with
relief depending on the track you choose.

## 2. Israeli taxation of the foreign rental income — two tracks (chosen annually)

| | **Track 1: 15% flat (Sec. 122A)** | **Track 2: marginal rate** |
|---|---|---|
| Base | **Gross** rent minus depreciation only | **Net** rent after all expenses + depreciation |
| Rate | 15% | Marginal, up to 47% (+3% surtax above ~₪721,560) |
| Expense deductions | None (depreciation only) | All |
| **Foreign tax credit** | **NO — local tax stacks on top** | **YES — full credit** |
| When it wins | Local tax low (Bulgaria), few expenses, high Israeli bracket | Local tax high (Greece upper brackets), low Israeli bracket, big expenses |

Approximate combined effective rates on rental income after the move:

| Country | Local tax | Track 1 total (local + 15%) | Track 2 total (high earner, 47%) |
|---|---|---|---|
| Bulgaria | ≈9% of gross | ≈24% of gross | ≈47% of net (credit for the 9%) |
| Italy (cedolare secca) | 21% of gross | ≈36% of gross | ≈47% of net (credit for the 21%) |
| Greece | 15–45% progressive | local + 15% of gross | ≈47% of net (credit for Greek tax) |

## 3. Returning-resident reliefs — the biggest planning lever

- **Ordinary returning resident (toshav chozer)** — abroad ≥6 consecutive years:
  foreign **passive** income (rent, interest, dividends) from assets **acquired while
  non-resident** is **exempt for 5 years**; capital gains on those assets exempt for **10 years**.
- **Veteran returning resident (toshav chozer vatik)** — abroad ≥10 consecutive years:
  **all foreign-source income and gains exempt for 10 years** (same as a new oleh).
- **Timing matters:** buy the property *before* re-establishing residency — the ordinary
  exemption only covers assets acquired while you were still non-resident.
- **Amendment 272 (in force for residents from 1 Jan 2026):** the 10-year **reporting**
  exemption is cancelled. Income remains tax-exempt, but foreign assets and income must be
  **declared from day one** (annual return + wealth declaration).

## 4. Capital gains at exit, as an Israeli resident

Israel: **25% on the real (inflation-adjusted) gain** (+2–3% surtax for high incomes), with a
foreign tax credit. Interaction per country:

| Country | Local CGT | Net result for Israeli resident |
|---|---|---|
| Bulgaria | 10% | Credit the 10%, top up ~15 pts to Israel |
| Italy | 26%, **0% after 5 years of ownership** | Within 5 yrs: credit the 26%, usually nothing more due. After 5 yrs: full 25% to Israel |
| Greece | suspended (0%) through 2026; 15% if reinstated | Full 25% to Israel while suspension holds |

Veteran returning residents: sale **within** the 10-year window is fully exempt in Israel;
after the window, the gain is apportioned linearly between exempt and taxable holding periods.

## 5. Local taxes that apply regardless of Israeli status

| | Sofia (Bulgaria) | Sicily (Italy) | Athens (Greece) |
|---|---|---|---|
| Rental income | 10% flat after 10% notional deduction (≈9% gross) | Cedolare secca 21% flat (26% from 2nd property); from 3rd short-let property treated as a business | 15% to €12k · 25% to €24k · 35% to €35k · 45% above (2026 scale) |
| Annual holding tax | ~0.15–0.45% municipal | IMU ~0.4–1.06% of cadastral value | ENFIA €2–16.2/m² + municipal fee |
| Purchase costs (approx.) | ~7% | ~12% (9% registration tax on second homes) | ~10% (3.09% transfer tax + fees) |

## 6. How this is modelled in the app

The financial engine (`app/backend/tax_engine.py`) computes after-tax yield and annual cash
flow per listing under four scenarios — `abroad`, `israel_15_track`, `israel_marginal_track`,
`returning_resident` — plus an exit-CGT estimate. Assumptions: depreciation 4%/yr on a 60%
building component; marginal rate configurable (default 47%); surtax not modelled (depends on
total income).

### Sources
- [PwC Tax Summaries — Israel: income determination](https://taxsummaries.pwc.com/israel/individual/income-determination) and [foreign tax relief](https://taxsummaries.pwc.com/israel/individual/foreign-tax-relief-and-tax-treaties)
- [PwC — Israel: returning-resident incentives](https://taxsummaries.pwc.com/israel/individual/other-tax-credits-and-incentives)
- [AACI — New disclosure rules for olim and returning Israelis, effective 1 Jan 2026](https://aaci.org.il/new-disclosure-rules-for-olim-and-returning-israelis-effective-1-1-2026/)
- [PwC Tax Summaries — Bulgaria: personal income](https://taxsummaries.pwc.com/bulgaria/individual/taxes-on-personal-income)
- [Global Property Guide — Bulgaria taxes](https://www.globalpropertyguide.com/europe/bulgaria/taxes-and-costs), [Italy taxes](https://www.globalpropertyguide.com/europe/italy/taxes-and-costs), [Greece taxes](https://www.globalpropertyguide.com/europe/greece/taxes-and-costs)
- [PwC Tax Summaries — Italy: income determination (cedolare secca, CGT 5-year exemption)](https://taxsummaries.pwc.com/italy/individual/income-determination)
- [TaxRavens — Greece personal income tax 2026 (new 25% rental bracket)](https://taxravens.com/en/blog/greece-personal-taxation)
- [Ellytic — Greece property taxes 2026 (ENFIA, CGT suspension)](https://ellytic.com/insights/greece-property-taxes-2026-updates)
- [Y-Tax — Israel–Bulgaria treaty](https://y-tax.co.il/en/country/israel-bulgaria-tax-treaty/), [property sale abroad](https://y-tax.co.il/en/property-sale-abroad/)
