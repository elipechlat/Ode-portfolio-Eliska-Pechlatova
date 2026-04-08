"""
scripts/geocode_missing.py — Geocode FarMappa locations that have an address but no GPS.

Uses the Nominatim OpenStreetMap geocoding API (free, no key required).
Respects the 1 req/sec usage policy with a 1-second delay between requests.

Strategy per address:
  1. Try the full address + ", Česká republika"
  2. If that fails, extract and try just the postal code + city
  3. If both fail, mark as unresolvable and move on

Usage (from project root):
    python scripts/geocode_missing.py           # geocode all missing
    python scripts/geocode_missing.py --limit 20  # test on first 20
"""

import argparse
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agents"))
from shared.db import get_connection

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    "User-Agent": "FarMappaBot/1.0 (open-source food map; github.com/FarMappa)",
    "Accept-Language": "cs,en",
}
REQUEST_DELAY = 1.1   # Nominatim policy: max 1 req/sec; add a little margin

# Matches a Czech postal code (5 digits, optionally space-separated: "123 45" or "12345")
_RE_POSTAL = re.compile(r"\b(\d{3})\s?(\d{2})\b")


def clean_address(raw: str) -> str:
    """Normalise whitespace and remove known noise characters."""
    return re.sub(r"\s+", " ", raw.replace("\xa0", " ").replace("–", "-")).strip()


def extract_postal_city(address: str) -> str | None:
    """
    Pull the postal code + the word(s) immediately after it.
    E.g. "182 00 Praha 8" → "18200 Praha 8, Česká republika"
    Returns None if no postal code is found.
    """
    m = _RE_POSTAL.search(address)
    if not m:
        return None
    # Everything from the postal code to end of string (strip leading/trailing junk)
    tail = address[m.start():].strip(" -–,")
    return tail


def nominatim_search(query: str) -> tuple[float, float] | None:
    """
    Search Nominatim for *query*. Returns (lat, lon) or None.
    Appends ", Česká republika" to bias results to CZ.
    """
    full_query = f"{query}, Česká republika"
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": full_query, "format": "json", "limit": 1,
                    "countrycodes": "cz"},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except (requests.RequestException, ValueError, KeyError):
        pass
    return None


def geocode_address(raw: str) -> tuple[float, float] | None:
    """
    Try three strategies to geocode *raw*:
      1. Full cleaned address
      2. Postal code + city tail only
      3. Postal code alone (returns town centroid — better than nothing)
    Returns (lat, lon) or None.
    """
    address = clean_address(raw)

    # Strategy 1: full address
    result = nominatim_search(address)
    if result:
        return result

    time.sleep(REQUEST_DELAY)

    # Strategy 2: postal code + city tail
    short = extract_postal_city(address)
    if short and short != address:
        result = nominatim_search(short)
        if result:
            return result
        time.sleep(REQUEST_DELAY)

    # Strategy 3: postal code alone
    m = _RE_POSTAL.search(address)
    if m:
        postal_only = m.group(1) + m.group(2)   # e.g. "29307"
        result = nominatim_search(postal_only)
        if result:
            return result

    return None


def main():
    parser = argparse.ArgumentParser(description="Geocode FarMappa locations missing GPS")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N locations (for testing).")
    args = parser.parse_args()

    conn = get_connection()

    rows = conn.execute("""
        SELECT id, name_cs, address
        FROM locations
        WHERE latitude IS NULL
          AND address IS NOT NULL
          AND TRIM(address) != ''
        ORDER BY id
    """).fetchall()

    if args.limit:
        rows = rows[: args.limit]

    total     = len(rows)
    succeeded = 0
    failed    = 0

    print(f"Geocoding {total} locations with missing GPS …\n")

    for i, row in enumerate(rows, start=1):
        loc_id  = row["id"]
        name    = row["name_cs"]
        address = row["address"]

        result = geocode_address(address)
        time.sleep(REQUEST_DELAY)

        if result:
            lat, lon = result
            conn.execute(
                "UPDATE locations SET latitude = ?, longitude = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (lat, lon, loc_id),
            )
            conn.commit()
            print(f"  [{i}/{total}] OK   {name[:45]:<45}  ({lat:.5f}, {lon:.5f})")
            succeeded += 1
        else:
            print(f"  [{i}/{total}] FAIL {name[:45]:<45}  addr: {address[:50]}")
            failed += 1

    conn.close()

    print(f"""
{'='*60}
GEOCODING COMPLETE
{'='*60}
  Processed : {total}
  Succeeded : {succeeded}
  Failed    : {failed}
  Success % : {100*succeeded//total if total else 0}%
{'='*60}""")


if __name__ == "__main__":
    main()
