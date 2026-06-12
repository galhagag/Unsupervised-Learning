"""Financial & tax analysis engine for cross-border property investments.

Models the after-tax economics of holding a rental property in Bulgaria,
Italy (Sicily) or Greece under four investor scenarios:

  1. abroad                  - investor is NOT an Israeli tax resident
  2. israel_15_track         - Israeli resident, Section 122A flat 15% track
  3. israel_marginal_track   - Israeli resident, marginal-rate track with
                               foreign tax credit
  4. returning_resident      - toshav chozer / toshav chozer vatik exemption
                               window (local tax only); requires 6+ consecutive
                               years abroad - gated by the years_abroad input

Each listing can be analysed under two rent strategies: a conservative
long let, or a short let (nightly rate x occupancy, with platform/management
costs and per-country licensing constraints).

All figures are annual EUR amounts unless stated otherwise. Rates encode the
law as of mid-2026 and are kept in one place so they are easy to audit and
update. This is decision-support modelling, not tax advice.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Country rules (situs taxation - always applies first under the treaties;
# Israel-Bulgaria, Israel-Italy and Israel-Greece treaties all give the
# situs country primary taxing rights over immovable property income).
# ---------------------------------------------------------------------------

GREECE_RENTAL_BRACKETS = [  # progressive, same for non-residents (2026)
    (12_000, 0.15),
    (24_000, 0.25),   # new 25% intermediate bracket from 1 Jan 2026
    (35_000, 0.35),
    (float("inf"), 0.45),
]


def greece_rental_tax(gross_rent: float) -> float:
    tax, lower = 0.0, 0.0
    for upper, rate in GREECE_RENTAL_BRACKETS:
        if gross_rent > lower:
            tax += (min(gross_rent, upper) - lower) * rate
            lower = upper
        else:
            break
    return tax


COUNTRY_RULES = {
    "bulgaria": {
        "label": "Bulgaria",
        # 10% flat on rental income after a statutory 10% notional expense
        # deduction => effective 9% of gross.
        "rental_tax": lambda gross, net: gross * 0.90 * 0.10,
        "rental_tax_note": "10% flat tax on gross rent after a statutory 10% "
                           "notional expense deduction (effective 9% of gross).",
        "cgt_rate": 0.10,
        "cgt_note": "10% on the gain for individuals.",
        "buy_costs_pct": 0.07,   # transfer tax ~3%, notary, agent, legal
    },
    "italy": {
        "label": "Italy (Sicily)",
        # Cedolare secca: flat 21% on gross residential rent (first property),
        # no expense deductions allowed under this regime.
        "rental_tax": lambda gross, net: gross * 0.21,
        "rental_tax_note": "Cedolare secca flat 21% on gross rent (first "
                           "property; 26% from the second). No expense "
                           "deductions under this regime. IMU is modelled as "
                           "an operating cost.",
        "cgt_rate": 0.26,
        "cgt_exempt_after_years": 5,
        "cgt_note": "26% if sold within 5 years of purchase; fully exempt "
                    "after 5 years of ownership.",
        "buy_costs_pct": 0.12,   # registration tax 9% (second home), notary, agent
    },
    "greece": {
        "label": "Greece",
        "rental_tax": lambda gross, net: greece_rental_tax(gross),
        "rental_tax_note": "Progressive rental tax: 15% to EUR 12k, 25% to "
                           "EUR 24k, 35% to EUR 35k, 45% above (2026 scale; "
                           "identical for non-residents). ENFIA is modelled "
                           "as an operating cost.",
        "cgt_rate": 0.0,
        "cgt_rate_after_suspension": 0.15,
        "cgt_note": "Individual CGT is suspended through 31 Dec 2026 (0%); "
                    "a 15% rate applies if the suspension lapses.",
        "buy_costs_pct": 0.10,   # transfer tax 3.09%, notary, agent, legal
    },
}

# ---------------------------------------------------------------------------
# Israeli rules
# ---------------------------------------------------------------------------

ISRAEL = {
    "flat_track_rate": 0.15,          # Section 122A
    "default_marginal_rate": 0.47,    # top bracket before surtax
    "cgt_rate": 0.25,                 # real gain, individuals
    "depreciation_rate": 0.04,        # annual, on building component
    "building_share_of_price": 0.60,  # assumed building (vs land) share
    "surtax_note": "A 3% surtax applies on total taxable income above "
                   "~ILS 721,560, plus an additional 2% on capital-source "
                   "income above the same threshold (2025+). Not modelled - "
                   "depends on the investor's total income.",
}

# Short-let economics: platform host fees + extra management/cleaning/
# utilities, as a share of short-let gross revenue.
SHORT_LET_COST_RATIO = 0.22

SHORT_LET_COUNTRY_NOTES = {
    "bulgaria": "Short lets require municipal categorisation as tourist "
                "accommodation. Income taxed like rental income at the 10% "
                "flat rate unless it rises to a business activity.",
    "italy": "National CIN registration code mandatory. Cedolare secca 21% "
             "applies to the first short-let property, 26% from the second, "
             "and from the third it is a business (ordinary tax + VAT).",
    "greece": "AMA registration number mandatory on every platform listing. "
              "NEW AMA registrations are frozen in central Athens districts "
              "1-3 (incl. Plaka, Koukaki, Kolonaki) until 31 Dec 2026 - a "
              "new buyer there cannot legally short-let. 3+ properties = "
              "professional status with 13% VAT.",
}

ISRAEL_SHORT_LET_NOTE = (
    "Israeli angle: an actively-managed short-let operation may be "
    "classified as BUSINESS income by the ITA, which would deny the 15% "
    "flat track and tax profits at marginal rates (with foreign tax "
    "credit). Using a local management company strengthens the passive "
    "characterisation."
)

SCENARIOS = {
    "abroad": {
        "label": "Living abroad (not an Israeli tax resident)",
        "description": "Only the country where the property sits taxes the "
                       "income. Israel has no claim while you are a foreign "
                       "tax resident.",
    },
    "israel_15_track": {
        "label": "Back in Israel - 15% flat track (Sec. 122A)",
        "description": "15% Israeli tax on gross foreign rent minus "
                       "depreciation only. No expense deductions and - "
                       "critically - NO credit for the foreign tax paid, so "
                       "it stacks on top of the local tax.",
    },
    "israel_marginal_track": {
        "label": "Back in Israel - marginal-rate track with foreign tax credit",
        "description": "Foreign rent is added to ordinary income and taxed "
                       "at the marginal rate (up to 47% + surtax) on NET "
                       "income after expenses and depreciation, with a "
                       "credit for the foreign tax paid.",
    },
    "returning_resident": {
        "label": "Back in Israel - returning-resident exemption window",
        "description": "Ordinary returning resident (6+ years abroad): "
                       "foreign passive income, incl. rent, from assets "
                       "acquired while abroad is exempt for 5 years. Veteran "
                       "returning resident (10+ years abroad): ALL foreign "
                       "income and gains exempt for 10 years. During the "
                       "window only local tax applies. Requires 6+ "
                       "consecutive years abroad - if not eligible, the "
                       "analysis falls back to the cheaper regular track.",
    },
}


@dataclass
class FinancialAnalysis:
    scenario: str
    gross_rent: float
    operating_expenses: float
    local_tax: float
    israeli_tax: float
    total_tax: float
    after_tax_income: float
    after_tax_yield_pct: float          # on all-in acquisition cost
    effective_tax_rate_pct: float       # of gross rent
    exit_cgt_estimate: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


def _israeli_flat_track(gross_rent: float, price: float) -> tuple[float, str]:
    depreciation = price * ISRAEL["building_share_of_price"] * ISRAEL["depreciation_rate"]
    base = max(0.0, gross_rent - depreciation)
    return base * ISRAEL["flat_track_rate"], (
        f"15% on gross rent minus depreciation (assumed "
        f"{ISRAEL['depreciation_rate']:.0%} on a "
        f"{ISRAEL['building_share_of_price']:.0%} building component = "
        f"EUR {depreciation:,.0f}/yr). No foreign tax credit on this track."
    )


def _israeli_marginal_track(net_income: float, local_tax: float,
                            marginal_rate: float, price: float) -> tuple[float, str]:
    depreciation = price * ISRAEL["building_share_of_price"] * ISRAEL["depreciation_rate"]
    taxable = max(0.0, net_income - depreciation)
    israeli_gross = taxable * marginal_rate
    israeli_net = max(0.0, israeli_gross - local_tax)
    return israeli_net, (
        f"{marginal_rate:.0%} on net income after expenses and depreciation "
        f"(EUR {taxable:,.0f} taxable), minus foreign tax credit of "
        f"EUR {min(local_tax, israeli_gross):,.0f}."
    )


def _exit_cgt(country: dict, price: float, assumed_gain_pct: float,
              scenario: str, holding_years: int = 6,
              years_abroad: int = 5) -> dict:
    gain = price * assumed_gain_pct
    local_rate = country["cgt_rate"]
    if country.get("cgt_exempt_after_years") and holding_years > country["cgt_exempt_after_years"]:
        local_rate = 0.0
    local_cgt = gain * local_rate

    if scenario == "abroad":
        israeli_cgt = 0.0
        note = "Israel does not tax the gain while you are a non-resident."
    elif scenario == "returning_resident" and years_abroad >= 6:
        israeli_cgt = 0.0
        note = ("Veteran returning resident: gain exempt if sold within the "
                "10-year window; after it, linear apportionment taxes only "
                "the post-window share. Ordinary returning resident: 10-year "
                "exemption applies to assets acquired abroad while non-resident.")
    else:
        israeli_gross = gain * ISRAEL["cgt_rate"]
        israeli_cgt = max(0.0, israeli_gross - local_cgt)
        note = (f"Israel taxes the real gain at {ISRAEL['cgt_rate']:.0%} with "
                f"a credit for the foreign CGT paid.")

    return {
        "assumed_gain_pct": assumed_gain_pct * 100,
        "assumed_holding_years": holding_years,
        "assumed_gain": round(gain),
        "local_cgt": round(local_cgt),
        "israeli_cgt_after_credit": round(israeli_cgt),
        "total_cgt": round(local_cgt + israeli_cgt),
        "local_rule": country["cgt_note"],
        "israeli_rule": note,
    }


def short_let_allowed(listing: dict) -> bool:
    return bool(listing.get("short_let", {}).get("allowed"))


def _rent_basis(listing: dict, rent_strategy: str) -> tuple[float, float, list]:
    """Return (gross_rent, opex, strategy_notes) for the chosen strategy."""
    if rent_strategy == "long_let":
        return (listing["expected_monthly_rent_eur"] * 12,
                listing["annual_operating_costs_eur"], [])
    if rent_strategy != "short_let":
        raise ValueError(f"Unknown rent_strategy '{rent_strategy}'. "
                         "Valid: ['long_let', 'short_let']")
    sl = listing.get("short_let") or {}
    if not sl.get("allowed"):
        raise ValueError(f"Short let not available for {listing['id']}: "
                         f"{sl.get('note', 'not permitted/modelled')}")
    gross = sl["nightly_rate_eur"] * 365 * sl["occupancy_pct"] / 100
    opex = (listing["annual_operating_costs_eur"]
            + gross * SHORT_LET_COST_RATIO)
    notes = [
        f"Short let modelled at EUR {sl['nightly_rate_eur']}/night x "
        f"{sl['occupancy_pct']}% occupancy; platform + management + extra "
        f"running costs at {SHORT_LET_COST_RATIO:.0%} of revenue.",
        SHORT_LET_COUNTRY_NOTES[listing["country"]],
        ISRAEL_SHORT_LET_NOTE,
    ]
    if sl.get("note"):
        notes.insert(1, sl["note"])
    return gross, opex, notes


def _mortgage(price: float, ltv: float, rate: float, term_years: int) -> dict | None:
    """French-annuity loan: annual debt service and first-year interest."""
    loan = price * ltv
    if loan <= 0:
        return None
    m, n = rate / 12, term_years * 12
    pmt = loan * m / (1 - (1 + m) ** -n) if m > 0 else loan / n
    balance, year1_interest = loan, 0.0
    for _ in range(12):
        interest = balance * m
        year1_interest += interest
        balance -= pmt - interest
    return {"loan_amount": round(loan),
            "annual_debt_service": round(pmt * 12),
            "year1_interest": round(year1_interest)}


def analyze(listing: dict, scenario: str = "abroad",
            marginal_rate: float | None = None,
            assumed_gain_pct: float = 0.25,
            holding_years: int = 6,
            rent_strategy: str = "long_let",
            years_abroad: int = 5,
            ltv: float = 0.0,
            mortgage_rate: float = 0.045,
            mortgage_term_years: int = 20) -> dict:
    """Run the full financial analysis for one listing under one scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. "
                         f"Valid: {list(SCENARIOS)}")
    country = COUNTRY_RULES[listing["country"]]
    marginal_rate = marginal_rate or ISRAEL["default_marginal_rate"]

    price = listing["price_eur"]
    all_in_cost = price * (1 + country["buy_costs_pct"])
    gross_rent, opex, strategy_notes = _rent_basis(listing, rent_strategy)
    net_income = gross_rent - opex

    mortgage = _mortgage(price, ltv, mortgage_rate, mortgage_term_years)
    interest_y1 = mortgage["year1_interest"] if mortgage else 0.0

    local_tax = country["rental_tax"](gross_rent, net_income)
    notes = [country["rental_tax_note"], *strategy_notes]
    if mortgage:
        notes.append("Financing does NOT reduce the local tax base in any of "
                     "the three countries (flat/gross-based regimes for "
                     "individuals). On the Israeli marginal track, year-1 "
                     "loan interest IS deductible; on the 15% flat track it "
                     "is not.")

    israeli_tax = 0.0
    if scenario == "israel_15_track":
        israeli_tax, note = _israeli_flat_track(gross_rent, price)
        notes.append(note)
    elif scenario == "israel_marginal_track":
        israeli_tax, note = _israeli_marginal_track(net_income - interest_y1,
                                                    local_tax,
                                                    marginal_rate, price)
        notes.append(note)
        notes.append(ISRAEL["surtax_note"])
    elif scenario == "returning_resident":
        if years_abroad < 6:
            # Not eligible: fall back to the cheaper of the two tracks.
            flat, _ = _israeli_flat_track(gross_rent, price)
            marg, _ = _israeli_marginal_track(net_income - interest_y1,
                                              local_tax,
                                              marginal_rate, price)
            israeli_tax = min(flat, marg)
            notes.append(f"NOT ELIGIBLE with {years_abroad} years abroad - "
                         "the exemption requires 6+ consecutive years of "
                         "foreign residency. Showing the cheaper of the two "
                         "regular tracks instead "
                         f"(EUR {israeli_tax:,.0f}/yr).")
        else:
            window = 10 if years_abroad >= 10 else 5
            notes.append(f"Eligible: {years_abroad} years abroad gives a "
                         f"{window}-year exemption window "
                         f"({'veteran - all foreign income' if window == 10 else 'ordinary - passive income from assets acquired while abroad'}). "
                         "Residents from 1 Jan 2026 must REPORT foreign "
                         "income/assets from day one even while exempt "
                         "(Amendment 272).")
    elif scenario == "abroad":
        notes.append("No Israeli tax while you are a foreign tax resident; "
                     "watch the residency tests (183-day / centre-of-life) "
                     "if you split time.")

    total_tax = local_tax + israeli_tax
    after_tax = net_income - total_tax

    financing = None
    if mortgage:
        equity = price * (1 - ltv) + price * country["buy_costs_pct"]
        cash_flow = after_tax - mortgage["annual_debt_service"]
        financing = {
            **mortgage,
            "ltv_pct": round(ltv * 100),
            "mortgage_rate_pct": round(mortgage_rate * 100, 2),
            "term_years": mortgage_term_years,
            "equity_invested": round(equity),
            "after_tax_cash_flow_after_debt": round(cash_flow),
            "cash_on_cash_pct": round(cash_flow / equity * 100, 2),
        }

    analysis = FinancialAnalysis(
        scenario=scenario,
        gross_rent=round(gross_rent),
        operating_expenses=round(opex),
        local_tax=round(local_tax),
        israeli_tax=round(israeli_tax),
        total_tax=round(total_tax),
        after_tax_income=round(after_tax),
        after_tax_yield_pct=round(after_tax / all_in_cost * 100, 2),
        effective_tax_rate_pct=round(total_tax / gross_rent * 100, 1),
        exit_cgt_estimate=_exit_cgt(country, price, assumed_gain_pct,
                                    scenario, holding_years, years_abroad),
        notes=notes,
    )
    return {
        "scenario": SCENARIOS[scenario] | {"id": scenario},
        "rent_strategy": rent_strategy,
        "all_in_acquisition_cost": round(all_in_cost),
        "buy_costs_pct": country["buy_costs_pct"] * 100,
        "gross_yield_pct": round(gross_rent / price * 100, 2),
        "net_pre_tax_yield_pct": round(net_income / all_in_cost * 100, 2),
        "financing": financing,
        **analysis.__dict__,
    }


def analyze_all_scenarios(listing: dict, marginal_rate: float | None = None,
                          years_abroad: int = 5, ltv: float = 0.0,
                          mortgage_rate: float = 0.045,
                          mortgage_term_years: int = 20) -> dict:
    """All scenarios x both rent strategies (short let only where allowed)."""
    out = {}
    for strategy in ("long_let", "short_let"):
        if strategy == "short_let" and not short_let_allowed(listing):
            out[strategy] = None
            continue
        out[strategy] = {
            s: analyze(listing, s, marginal_rate, rent_strategy=strategy,
                       years_abroad=years_abroad, ltv=ltv,
                       mortgage_rate=mortgage_rate,
                       mortgage_term_years=mortgage_term_years)
            for s in SCENARIOS
        }
    return out
