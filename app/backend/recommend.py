"""Best-pick recommendation: blends hold-period IRR with the asset score and
applies the investor's equity budget, then writes a plain-language rationale.
"""

import projection
import scoring


def _profile_to_assumptions(profile: dict, listing: dict) -> projection.ProfileAssumptions:
    return projection.ProfileAssumptions(
        years_abroad_at_purchase=profile.get("years_abroad_at_purchase", 5),
        move_back_year=profile.get("move_back_year"),
        marginal_rate=profile.get("marginal_rate", 0.47),
        hold_years=profile.get("hold_years", 10),
        rent_growth_pct=profile.get("rent_growth_pct", 2.5),
        appreciation_pct=profile.get("appreciation_pct", 3.0),
        vacancy_pct=profile.get("vacancy_pct", 5.0),
        discount_rate_pct=profile.get("discount_rate_pct", 7.0),
        rent_strategy=(profile.get("rent_strategy", "long_let")
                       if listing.get("short_let", {}).get("allowed")
                       or profile.get("rent_strategy") != "short_let"
                       else "long_let"),
        ltv=profile.get("ltv", 0.0),
        mortgage_rate=profile.get("mortgage_rate", 0.045),
        mortgage_term_years=profile.get("mortgage_term_years", 20),
    )


def evaluate(listings: list[dict], profile: dict) -> list[dict]:
    """Score every listing on a 0-100 'fit' = 55% IRR-derived + 45% asset score,
    with an affordability flag against the equity budget."""
    budget = profile.get("equity_budget_eur")
    out = []
    for l in listings:
        assumptions = _profile_to_assumptions(profile, l)
        proj = projection.project(l, assumptions)
        asset = scoring.score(l)
        irr = proj["metrics"]["irr_pct"]
        # Map IRR 0%->0, 12%+->100 for the fit blend.
        irr_component = max(0.0, min(100.0, (irr or 0) / 12 * 100))
        fit = round(0.55 * irr_component + 0.45 * asset["total"], 1)
        affordable = budget is None or proj["equity_invested"] <= budget
        out.append({
            "id": l["id"], "title": l["title"], "city": l["city"],
            "price_eur": l["price_eur"],
            "fit_score": fit, "asset_score": asset["total"],
            "asset_grade": asset["grade"], "irr_pct": irr,
            "npv": proj["metrics"]["npv"],
            "total_after_tax_profit": proj["metrics"]["total_after_tax_profit"],
            "equity_invested": proj["equity_invested"],
            "affordable": affordable,
            "area": asset["area"], "area_verdict": asset["area_verdict"],
        })
    out.sort(key=lambda r: (r["affordable"], r["fit_score"]), reverse=True)
    return out


def recommend(listings: list[dict], profile: dict) -> dict:
    ranked = evaluate(listings, profile)
    if not ranked:
        return {"ranked": [], "top_pick": None, "per_city": {}, "rationale": ""}
    affordable = [r for r in ranked if r["affordable"]] or ranked
    top = affordable[0]
    runner = affordable[1] if len(affordable) > 1 else None

    per_city = {}
    for r in ranked:                      # best in each city, budget-flagged
        if r["city"] not in per_city:
            per_city[r["city"]] = r

    rationale = (
        f"{top['title']} ({top['city']}) is the best fit: fit score "
        f"{top['fit_score']}/100 from a projected {top['irr_pct']}% IRR and an "
        f"asset grade of {top['asset_grade']}. Over the hold it returns an "
        f"estimated EUR {top['total_after_tax_profit']:,} after tax on "
        f"EUR {top['equity_invested']:,} equity"
        + (f", inside your EUR {profile['equity_budget_eur']:,} budget."
           if profile.get("equity_budget_eur") else ".")
    )
    if runner:
        gap = round(top["fit_score"] - runner["fit_score"], 1)
        rationale += (f" It edges out {runner['title']} ({runner['city']}, fit "
                      f"{runner['fit_score']}) by {gap} points"
                      + (f", chiefly on IRR ({top['irr_pct']}% vs {runner['irr_pct']}%)."
                         if (top['irr_pct'] or 0) != (runner['irr_pct'] or 0)
                         else " on overall asset quality."))
    unaffordable = [r for r in ranked if not r["affordable"]]
    if unaffordable and profile.get("equity_budget_eur"):
        rationale += (f" {len(unaffordable)} higher-priced listing(s) were "
                      f"ranked below budget-fit.")
    return {"ranked": ranked, "top_pick": top, "runner_up": runner,
            "per_city": per_city, "rationale": rationale}
