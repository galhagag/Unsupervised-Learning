"""Paste-any-listing extraction.

Turns raw listing text in any language (Bulgarian, Greek, Italian, English,
Hebrew...) into a structured listing the analysis engine can consume.

Two extraction paths:
  1. LLM (preferred): Claude with structured outputs - set ANTHROPIC_API_KEY.
  2. Heuristic fallback: regex extraction of price / size / rent so the
     feature still works without a key (lower fidelity, flagged as such).

Saved listings persist to data/manual_listings.json and join the pool as
the 'manual' source.
"""

import json
import os
import re
import time
from pathlib import Path

from pydantic import BaseModel, Field

from scrapers.common import CITY_ESTIMATES, parse_number, to_listing

MANUAL_FILE = Path(__file__).parent / "data" / "manual_listings.json"

EUR_PER_BGN = 1 / 1.95583


class ExtractedListing(BaseModel):
    """Schema Claude fills in from the pasted text."""
    title: str = Field(description="Short English title, e.g. '2-bed apartment, Lozenets, 74 m2'")
    price_eur: int = Field(description="Asking price converted to EUR (BGN/1.95583 if priced in leva)")
    size_m2: float | None = Field(default=None, description="Living area in square meters")
    neighborhood: str = Field(default="", description="District/neighborhood name, transliterated to Latin script")
    monthly_rent_eur: int | None = Field(default=None, description="Monthly rent in EUR ONLY if explicitly stated in the text; otherwise null")
    overview: str = Field(description="2-3 sentence English summary of the listing")
    highlights: list[str] = Field(default_factory=list, description="Up to 4 notable positives stated in the text")
    risks: list[str] = Field(default_factory=list, description="Up to 3 concerns evident from the text (age, floor, legal status, needs renovation...)")
    source_language: str = Field(default="", description="Language of the original text")


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def extract_with_llm(text: str) -> tuple[dict, str]:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model="claude-opus-4-8",
        max_tokens=4096,
        system="You extract structured data from real-estate listings. The "
               "text may be in Bulgarian, Greek, Italian, English or Hebrew. "
               "Convert all amounts to EUR (1 EUR = 1.95583 BGN). Be "
               "conservative: only fill monthly_rent_eur if the text "
               "explicitly states a rent figure.",
        messages=[{"role": "user", "content": f"Extract the listing fields "
                   f"from this text:\n\n{text[:8000]}"}],
        output_format=ExtractedListing,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise ValueError("LLM returned no parseable output")
    return parsed.model_dump(), "llm (claude-opus-4-8)"


# --- Heuristic fallback ----------------------------------------------------

PRICE_PATTERNS = [
    r"(?:€|EUR|euro)\s*([\d][\d\s.,]{3,12})",
    r"([\d][\d\s.,]{3,12})\s*(?:€|EUR|euro)",
    r"([\d][\d\s.,]{3,12})\s*(?:лв|BGN|лева)",
]
SIZE_PATTERN = r"(\d{2,4}(?:[.,]\d{1,2})?)\s*(?:m²|m2|кв\.?\s?м|sq\.?\s?m|sqm|τ\.?μ\.?|mq)"
RENT_PATTERN = r"(?:rent|наем|affitto|ενοίκιο)\D{0,20}([\d][\d\s.,]{2,8})"


def extract_heuristic(text: str) -> tuple[dict, str]:
    price = None
    for i, pat in enumerate(PRICE_PATTERNS):
        m = re.search(pat, text, re.I)
        if m:
            price = parse_number(m.group(1))
            if price and i == 2:               # BGN pattern
                price *= EUR_PER_BGN
            if price and price >= 20_000:
                break
            price = None
    size_m = re.search(SIZE_PATTERN, text, re.I)
    rent_m = re.search(RENT_PATTERN, text, re.I)
    first_line = next((l.strip() for l in text.splitlines() if l.strip()), "Pasted listing")
    out = {
        "title": first_line[:100],
        "price_eur": round(price) if price else None,
        "size_m2": parse_number(size_m.group(1)) if size_m else None,
        "neighborhood": "",
        "monthly_rent_eur": round(parse_number(rent_m.group(1))) if rent_m else None,
        "overview": text.strip()[:350],
        "highlights": [],
        "risks": ["Heuristic extraction (no LLM key set) - verify every field"],
        "source_language": "",
    }
    return out, "heuristic (regex; set ANTHROPIC_API_KEY for LLM extraction)"


# --- Pipeline ---------------------------------------------------------------

def extract(text: str, city: str) -> dict:
    """Extract fields and map onto the listing schema (without saving)."""
    if city not in CITY_ESTIMATES:
        raise ValueError(f"city must be one of {list(CITY_ESTIMATES)}")
    if not text or len(text.strip()) < 30:
        raise ValueError("Paste at least the core of the listing text (30+ chars).")

    if llm_available():
        fields, method = extract_with_llm(text)
    else:
        fields, method = extract_heuristic(text)

    if not fields.get("price_eur"):
        raise ValueError("Could not find an asking price in the text - add "
                         "it (e.g. '€139,000') and retry.")

    listing = to_listing(
        portal="manual",
        portal_id=str(int(time.time() * 1000)),
        city=city,
        title=fields["title"],
        price_eur=fields["price_eur"],
        size_m2=fields.get("size_m2"),
        neighborhood=fields.get("neighborhood", ""),
        url="",
        overview=fields.get("overview", ""),
    )
    if listing is None:
        raise ValueError("Price below the EUR 20k plausibility floor - "
                         "check the extracted amount.")
    # Stated rent beats the city-level estimate.
    if fields.get("monthly_rent_eur"):
        listing["expected_monthly_rent_eur"] = fields["monthly_rent_eur"]
        listing["rent_basis"] = "stated in listing"
    else:
        listing["rent_basis"] = "city-level estimate"
    listing["data_source"] = "manual (pasted)"
    listing["listing_url"] = ""
    listing["highlights"] = fields.get("highlights") or ["Manually added listing"]
    listing["risks"] = (fields.get("risks") or []) + [
        "Manually entered - verify against the original listing"]
    listing["extraction_method"] = method
    listing["added_at"] = time.strftime("%Y-%m-%d")
    return listing


def load_manual() -> list:
    if MANUAL_FILE.exists():
        return json.loads(MANUAL_FILE.read_text())
    return []


def save_manual(listing: dict) -> dict:
    listings = load_manual()
    listings.append(listing)
    MANUAL_FILE.write_text(json.dumps(listings, indent=2, ensure_ascii=False))
    return listing


def delete_manual(listing_id: str) -> bool:
    listings = load_manual()
    kept = [l for l in listings if l["id"] != listing_id]
    if len(kept) == len(listings):
        return False
    MANUAL_FILE.write_text(json.dumps(kept, indent=2, ensure_ascii=False))
    return True
