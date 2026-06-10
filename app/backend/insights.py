"""Lightweight market-intelligence helpers: FX overlay, comparables from the
history DB, price-drop detection, and ownership alerts.
"""

import time

import history

# EUR/ILS reference rate. Static fallback; a live feed can replace this when
# outbound HTTP is available (see fetch note). Kept in one place.
EUR_ILS = 3.95
EUR_ILS_AS_OF = "2026-06 (static reference)"


def with_ils(amount_eur: float | None) -> float | None:
    return round(amount_eur * EUR_ILS) if amount_eur is not None else None


def comparables(listing: dict, all_listings: list[dict]) -> dict:
    """Compare a listing's EUR/m2 against same-city (and same-area when known)
    peers drawn from the current pool plus the history DB."""
    target_ppm2 = listing["price_eur"] / listing["size_m2"]
    pool = {l["id"]: l for l in all_listings}
    for row in history.query(city=listing["city"]):
        if row["id"] not in pool and row.get("size_m2"):
            pool[row["id"]] = {"id": row["id"], "city": row["city"],
                               "price_eur": row["price_eur"],
                               "size_m2": row["size_m2"],
                               "neighborhood": row.get("neighborhood", "")}
    peers = [l for l in pool.values()
             if l["city"] == listing["city"] and l["id"] != listing["id"]
             and l.get("size_m2")]
    ppm2 = sorted(l["price_eur"] / l["size_m2"] for l in peers)
    if not ppm2:
        return {"target_eur_m2": round(target_ppm2), "peer_count": 0}
    median = ppm2[len(ppm2) // 2]
    cheaper = sum(1 for v in ppm2 if v < target_ppm2)
    return {
        "target_eur_m2": round(target_ppm2),
        "peer_count": len(ppm2),
        "median_eur_m2": round(median),
        "percentile": round(cheaper / len(ppm2) * 100),
        "verdict": ("below-market" if target_ppm2 < median * 0.95
                    else "above-market" if target_ppm2 > median * 1.05
                    else "at-market"),
    }


def price_changes() -> list[dict]:
    """Listings whose price moved between first and last sighting (history DB
    stores current price; first_seen vs last_seen dates flag re-sights)."""
    out = []
    for row in history.query():
        if row.get("first_seen") and row.get("last_seen") \
                and row["first_seen"] != row["last_seen"]:
            out.append({"id": row["id"], "title": row["title"],
                        "city": row["city"], "price_eur": row["price_eur"],
                        "first_seen": row["first_seen"],
                        "last_seen": row["last_seen"],
                        "status": row["status"]})
    return out


def ownership_alerts(properties: list[dict], profile: dict,
                     obligations: dict) -> list[dict]:
    """Forward-looking alerts: tax milestones, exemption-window expiry, and
    obligation reminders for owned properties."""
    alerts = []
    today = time.strftime("%Y-%m-%d")
    move_back = profile.get("move_back_year")
    years_abroad = profile.get("years_abroad_at_purchase", 5)

    if move_back and years_abroad >= 6:
        window = 10 if years_abroad >= 10 else 5
        alerts.append({
            "severity": "info",
            "title": "Returning-resident exemption window",
            "detail": f"Foreign income is exempt for {window} years from your "
                      f"move-back (hold-year {move_back}). Plan a sale or "
                      f"regime switch before year {move_back + window}.",
        })
    elif move_back:
        alerts.append({
            "severity": "warning",
            "title": "No returning-resident exemption",
            "detail": "With <6 years abroad, Israeli tax applies from the "
                      "move-back year on top of local tax. Compare the 15% "
                      "flat track vs the marginal track each year.",
        })

    for prop in properties:
        if prop["country"] == "italy" and prop.get("purchase_date"):
            alerts.append({
                "severity": "info",
                "title": f"Italy 5-year CGT-free date — {prop['title']}",
                "detail": f"Bought {prop['purchase_date']}: a sale 5 years "
                          f"after this date is exempt from Italian capital "
                          f"gains tax.",
            })
        country_obs = obligations["countries"].get(prop["country"], {})
        for ob in country_obs.get("obligations", [])[:2]:
            alerts.append({
                "severity": "reminder",
                "title": f"{ob['title']} — {prop['title']}",
                "detail": f"{ob['frequency'].title()}, due {ob['due']}.",
                "link": ob.get("link"),
            })
    return alerts
