"""Smarter-decisions engines: move-back timing planner, exit-year optimizer,
and Monte Carlo risk bands.

All three sweep the deterministic projection engine with varied inputs - no
new tax logic lives here.
"""

import random
import statistics

import insights
import projection


def _assumptions(profile: dict, **overrides) -> projection.ProfileAssumptions:
    base = dict(
        years_abroad_at_purchase=profile.get("years_abroad_at_purchase", 5),
        move_back_year=profile.get("move_back_year"),
        marginal_rate=profile.get("marginal_rate", 0.47),
        hold_years=profile.get("hold_years", 10),
        rent_growth_pct=profile.get("rent_growth_pct", 2.5),
        appreciation_pct=profile.get("appreciation_pct", 3.0),
        vacancy_pct=profile.get("vacancy_pct", 5.0),
        discount_rate_pct=profile.get("discount_rate_pct", 7.0),
        rent_strategy=profile.get("rent_strategy", "long_let"),
        ltv=profile.get("ltv", 0.0),
        mortgage_rate=profile.get("mortgage_rate", 0.045),
        mortgage_term_years=profile.get("mortgage_term_years", 20),
    )
    base.update(overrides)
    return projection.ProfileAssumptions(**base)


def move_back_planner(listing: dict, profile: dict) -> dict:
    """Sweep the move-back year. Key subtlety: delaying the return also
    grows your years abroad - crossing 6 (ordinary) or 10 (veteran)
    unlocks the returning-resident exemption, which can be worth more
    than the extra years of waiting.
    """
    years_abroad_now = profile.get("years_abroad_at_purchase", 5)
    hold = profile.get("hold_years", 10)
    if listing.get("short_let", {}).get("allowed") is False \
            and profile.get("rent_strategy") == "short_let":
        profile = {**profile, "rent_strategy": "long_let"}

    rows = []
    for mb_year in list(range(1, hold + 1)) + [None]:        # None = stay abroad
        years_abroad_at_return = (years_abroad_now + mb_year
                                  if mb_year is not None else years_abroad_now)
        # projection accrues abroad-years to the move-back itself
        a = _assumptions(profile, move_back_year=mb_year)
        m = projection.project(listing, a)["metrics"]
        exemption = ("none" if mb_year is None
                     else "veteran (10y)" if years_abroad_at_return >= 10
                     else "ordinary (5y)" if years_abroad_at_return >= 6
                     else "not eligible")
        rows.append({
            "move_back_year": mb_year,
            "years_abroad_at_return": years_abroad_at_return if mb_year else None,
            "exemption": exemption,
            "irr_pct": m["irr_pct"],
            "total_after_tax_profit": m["total_after_tax_profit"],
        })

    current = next((r for r in rows
                    if r["move_back_year"] == profile.get("move_back_year")), rows[0])
    movers = [r for r in rows if r["move_back_year"] is not None]
    best = max(movers, key=lambda r: r["total_after_tax_profit"])
    delta = best["total_after_tax_profit"] - current["total_after_tax_profit"]

    # The cliff: first move-back year that reaches 6 years abroad.
    cliff_year = max(1, 6 - years_abroad_now)
    note = ""
    if years_abroad_now < 6:
        cliff_row = next((r for r in movers if r["move_back_year"] == cliff_year), None)
        if cliff_row and current["move_back_year"] is not None \
                and current["move_back_year"] < cliff_year:
            gain = cliff_row["total_after_tax_profit"] - current["total_after_tax_profit"]
            note = (f"Delaying your return to hold-year {cliff_year} crosses "
                    f"the 6-consecutive-years line and unlocks the 5-year "
                    f"returning-resident exemption - worth "
                    f"EUR {gain:,} (~ILS {insights.with_ils(gain):,}) over "
                    f"this hold vs returning in year "
                    f"{current['move_back_year']}.")
    return {
        "listing_id": listing["id"],
        "current_plan": current,
        "best_plan": best,
        "improvement_eur": round(delta),
        "improvement_ils": insights.with_ils(delta),
        "six_year_cliff_note": note,
        "rows": rows,
    }


def exit_optimizer(listing: dict, profile: dict,
                   min_hold: int = 2, max_hold: int = 15) -> dict:
    """Sweep the sale year and find the IRR-maximizing exit - this is where
    Italy's 5-year CGT cliff and the exemption-window expiry show up."""
    rows = []
    for hold in range(min_hold, max_hold + 1):
        a = _assumptions(profile, hold_years=hold)
        out = projection.project(listing, a)
        rows.append({
            "sale_year": hold,
            "irr_pct": out["metrics"]["irr_pct"],
            "total_after_tax_profit": out["metrics"]["total_after_tax_profit"],
            "local_cgt": out["exit"]["local_cgt"],
            "israeli_cgt": out["exit"]["israeli_cgt"],
        })
    by_irr = max(rows, key=lambda r: r["irr_pct"] or -99)
    by_profit = max(rows, key=lambda r: r["total_after_tax_profit"])
    notes = []
    if listing["country"] == "italy":
        notes.append("Italy: selling in year 6+ drops the local CGT to zero - "
                     "watch the cliff between years 5 and 6.")
    return {"listing_id": listing["id"], "best_irr": by_irr,
            "best_profit": by_profit, "rows": rows, "notes": notes}


def monte_carlo(listing: dict, profile: dict, draws: int = 300,
                seed: int | None = 42) -> dict:
    """IRR distribution under uncertainty in rent growth, appreciation,
    vacancy and the rent level itself."""
    rng = random.Random(seed)
    base_rent_growth = profile.get("rent_growth_pct", 2.5)
    base_appreciation = profile.get("appreciation_pct", 3.0)

    irrs, profits, neg_cf = [], [], 0
    for _ in range(draws):
        scaled = dict(listing)
        rent_scale = rng.uniform(0.85, 1.10)        # rent estimate error
        scaled["expected_monthly_rent_eur"] = listing["expected_monthly_rent_eur"] * rent_scale
        if scaled.get("short_let", {}).get("allowed"):
            sl = dict(scaled["short_let"])
            sl["nightly_rate_eur"] = sl["nightly_rate_eur"] * rent_scale
            scaled["short_let"] = sl
        a = _assumptions(
            profile,
            rent_growth_pct=rng.gauss(base_rent_growth, 1.5),
            appreciation_pct=rng.gauss(base_appreciation, 2.0),
            vacancy_pct=min(25.0, max(0.0, rng.uniform(2.0, 12.0))),
        )
        m = projection.project(scaled, a)["metrics"]
        if m["irr_pct"] is not None:
            irrs.append(m["irr_pct"])
        profits.append(m["total_after_tax_profit"])
        if m["avg_annual_cash_flow"] < 0:
            neg_cf += 1

    irrs.sort()
    profits.sort()

    def pct(data, p):
        return round(data[min(len(data) - 1, int(p / 100 * len(data)))], 2)

    return {
        "listing_id": listing["id"],
        "draws": draws,
        "irr": {"p10": pct(irrs, 10), "p50": pct(irrs, 50), "p90": pct(irrs, 90)},
        "profit": {"p10": round(pct(profits, 10)), "p50": round(pct(profits, 50)),
                   "p90": round(pct(profits, 90))},
        "prob_negative_cash_flow_pct": round(neg_cf / draws * 100, 1),
        "prob_loss_pct": round(sum(1 for p in profits if p < 0) / draws * 100, 1),
        "irr_stdev": round(statistics.stdev(irrs), 2) if len(irrs) > 1 else None,
        "assumption_ranges": "rent level x0.85-1.10, rent growth N(base,1.5), "
                             "appreciation N(base,2.0), vacancy U(2,12)%",
    }
