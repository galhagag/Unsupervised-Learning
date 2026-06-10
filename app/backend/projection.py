"""Hold-period projection engine.

Turns a single-year snapshot into a multi-year after-tax cash-flow model and
the metrics that actually answer "which listing is best for ME":

  - year-by-year net operating income, tax, debt service, free cash flow
  - the move-back-to-Israel year switching the tax regime mid-hold
  - returning-resident exemption window opening/closing
  - Italy's 5-year CGT-free milestone at exit
  - terminal sale: appreciation, local + Israeli CGT with credit
  - IRR, NPV, equity multiple, total after-tax profit

This is decision-support modelling, not tax advice. Defaults are explicit
and overridable via the InvestorProfile.
"""

from dataclasses import dataclass, field

import tax_engine


@dataclass
class ProfileAssumptions:
    years_abroad_at_purchase: int = 5   # <6 => no returning-resident relief
    move_back_year: int | None = None   # hold-year index (1-based) you re-become Israeli resident
    marginal_rate: float = 0.47
    hold_years: int = 10
    rent_growth_pct: float = 2.5        # annual
    appreciation_pct: float = 3.0       # annual capital growth
    vacancy_pct: float = 5.0            # of gross rent
    opex_growth_pct: float = 2.0
    capex_reserve_pct: float = 1.0      # of property value/yr set aside
    discount_rate_pct: float = 7.0      # for NPV
    selling_cost_pct: float = 3.0       # agent/legal on exit
    rent_strategy: str = "long_let"
    ltv: float = 0.0
    mortgage_rate: float = 0.045
    mortgage_term_years: int = 20


def _scenario_for_year(year: int, p: ProfileAssumptions) -> str:
    """Which tax regime applies in a given hold-year."""
    if p.move_back_year is None or year < p.move_back_year:
        return "abroad"
    years_back = year - p.move_back_year                 # 0 in the move-back year
    total_years_abroad = p.years_abroad_at_purchase      # at the moment of return
    if total_years_abroad >= 6:
        window = 10 if total_years_abroad >= 10 else 5
        if years_back < window:
            return "returning_resident"
    # exemption expired or never applied: pick the cheaper regular track
    return "_cheaper_track"


def _annual_tax(listing, scenario, gross_rent, opex, interest, p) -> tuple[float, str]:
    """Israeli + local tax for one year at a given gross rent / opex level."""
    # Build a per-year synthetic listing so tax_engine uses this year's rent.
    synthetic = dict(listing,
                     expected_monthly_rent_eur=gross_rent / 12,
                     annual_operating_costs_eur=opex)
    if scenario == "_cheaper_track":
        flat = tax_engine.analyze(synthetic, "israel_15_track",
                                  marginal_rate=p.marginal_rate,
                                  rent_strategy=p.rent_strategy, ltv=p.ltv,
                                  mortgage_rate=p.mortgage_rate,
                                  mortgage_term_years=p.mortgage_term_years)
        marg = tax_engine.analyze(synthetic, "israel_marginal_track",
                                  marginal_rate=p.marginal_rate,
                                  rent_strategy=p.rent_strategy, ltv=p.ltv,
                                  mortgage_rate=p.mortgage_rate,
                                  mortgage_term_years=p.mortgage_term_years)
        if flat["total_tax"] <= marg["total_tax"]:
            return flat["total_tax"], "Israel 15% flat track (cheaper this year)"
        return marg["total_tax"], "Israel marginal track + FTC (cheaper this year)"
    res = tax_engine.analyze(synthetic, scenario, marginal_rate=p.marginal_rate,
                             years_abroad=p.years_abroad_at_purchase,
                             rent_strategy=p.rent_strategy, ltv=p.ltv,
                             mortgage_rate=p.mortgage_rate,
                             mortgage_term_years=p.mortgage_term_years)
    label = {"abroad": "Non-resident: local tax only",
             "returning_resident": "Returning-resident exemption (local tax only)"}.get(
                 scenario, scenario)
    return res["total_tax"], label


def _irr(cash_flows: list[float], lo=-0.9, hi=1.0) -> float | None:
    """Bisection IRR. cash_flows[0] is the (negative) initial equity."""
    def npv(r):
        return sum(cf / (1 + r) ** i for i, cf in enumerate(cash_flows))
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        v = npv(mid)
        if abs(v) < 1:
            return mid
        if npv(lo) * v < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def project(listing: dict, profile: ProfileAssumptions) -> dict:
    p = profile
    country = tax_engine.COUNTRY_RULES[listing["country"]]
    price = listing["price_eur"]
    all_in = price * (1 + country["buy_costs_pct"])

    base_gross, base_opex, _ = tax_engine._rent_basis(listing, p.rent_strategy)

    mortgage = tax_engine._mortgage(price, p.ltv, p.mortgage_rate, p.mortgage_term_years)
    debt_service = mortgage["annual_debt_service"] if mortgage else 0.0
    loan = mortgage["loan_amount"] if mortgage else 0.0
    interest_y1 = mortgage["year1_interest"] if mortgage else 0.0
    equity_in = all_in - loan

    rows, cash_flows = [], [-equity_in]
    npv = -equity_in
    for year in range(1, p.hold_years + 1):
        gross = base_gross * (1 + p.rent_growth_pct / 100) ** (year - 1)
        gross_after_vac = gross * (1 - p.vacancy_pct / 100)
        opex = base_opex * (1 + p.opex_growth_pct / 100) ** (year - 1)
        value = price * (1 + p.appreciation_pct / 100) ** year
        capex = value * p.capex_reserve_pct / 100
        scenario = _scenario_for_year(year, p)
        tax, tax_label = _annual_tax(listing, scenario, gross_after_vac, opex,
                                     interest_y1, p)
        fcf = gross_after_vac - opex - tax - debt_service - capex
        cash_flows.append(fcf)
        npv += fcf / (1 + p.discount_rate_pct / 100) ** year
        rows.append({
            "year": year, "scenario": scenario, "tax_label": tax_label,
            "gross_rent": round(gross_after_vac), "opex": round(opex),
            "tax": round(tax), "debt_service": round(debt_service),
            "capex_reserve": round(capex), "free_cash_flow": round(fcf),
            "property_value": round(value),
        })

    # Terminal sale in the final year.
    sale_value = price * (1 + p.appreciation_pct / 100) ** p.hold_years
    selling_costs = sale_value * p.selling_cost_pct / 100
    gain = sale_value - price
    exit_scenario = _scenario_for_year(p.hold_years, p)
    local_rate = country["cgt_rate"]
    if country.get("cgt_exempt_after_years") and p.hold_years > country["cgt_exempt_after_years"]:
        local_rate = 0.0
    local_cgt = max(0.0, gain) * local_rate
    if exit_scenario in ("abroad", "returning_resident"):
        israeli_cgt = 0.0
        cgt_note = ("No Israeli CGT (non-resident or within the "
                    "returning-resident exemption window).")
    else:
        israeli_cgt = max(0.0, max(0.0, gain) * tax_engine.ISRAEL["cgt_rate"] - local_cgt)
        cgt_note = "Israeli 25% CGT on the gain, less credit for foreign CGT."
    net_sale = sale_value - selling_costs - local_cgt - israeli_cgt - loan
    cash_flows[-1] += net_sale
    npv += net_sale / (1 + p.discount_rate_pct / 100) ** p.hold_years

    total_cf = sum(cash_flows)
    irr = _irr(cash_flows)
    return {
        "assumptions": p.__dict__,
        "equity_invested": round(equity_in),
        "all_in_cost": round(all_in),
        "years": rows,
        "exit": {
            "sale_value": round(sale_value), "selling_costs": round(selling_costs),
            "gain": round(gain), "local_cgt": round(local_cgt),
            "israeli_cgt": round(israeli_cgt), "loan_repaid": round(loan),
            "net_sale_proceeds": round(net_sale), "scenario": exit_scenario,
            "note": cgt_note, "local_cgt_rate": local_rate,
        },
        "metrics": {
            "irr_pct": round(irr * 100, 2) if irr is not None else None,
            "npv": round(npv),
            "equity_multiple": round((total_cf + equity_in) / equity_in, 2) if equity_in else None,
            "total_after_tax_profit": round(total_cf),
            "avg_annual_cash_flow": round(sum(r["free_cash_flow"] for r in rows) / p.hold_years),
        },
        "milestones": _milestones(listing, country, p),
    }


def _milestones(listing, country, p: ProfileAssumptions) -> list:
    out = []
    if p.move_back_year:
        out.append(f"Year {p.move_back_year}: you re-become an Israeli tax "
                   f"resident — worldwide income taxable from here.")
        if p.years_abroad_at_purchase >= 6:
            window = 10 if p.years_abroad_at_purchase >= 10 else 5
            out.append(f"Years {p.move_back_year}-{p.move_back_year + window - 1}: "
                       f"returning-resident exemption — foreign income exempt.")
        else:
            out.append("No returning-resident exemption (<6 years abroad): "
                       "Israeli tax applies immediately on top of local tax.")
    if country.get("cgt_exempt_after_years"):
        out.append(f"Year {country['cgt_exempt_after_years'] + 1}+: local capital "
                   f"gains tax falls to 0% (Italy 5-year rule).")
    return out
