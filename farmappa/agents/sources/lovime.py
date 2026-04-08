"""
agents/sources/lovime.py — FarMappa data source for lovime.bio

The original biospotrebitel.cz redirected here (run by Pro-Bio Liga).
Uses the public JSON API at api.lovime.bio — no authentication required.

Two-stage fetch:
  1. POST /filter  — returns all ~450 listings (name, GPS, phone, specializations)
  2. GET /place/id — returns full detail per listing (description, website, email, address)
"""

import json
import time

import requests

from shared.base_source import BaseSource
from shared.categories import map_specializations
from shared.utils import parse_gps

API_BASE      = "https://api.lovime.bio"
FILTER_URL    = f"{API_BASE}/filter"
PLACE_URL     = f"{API_BASE}/place"
REQUEST_DELAY = 0.3   # seconds between detail requests — be polite

HEADERS = {
    "User-Agent": "FarMappaBot/1.0 (open-source food map; github.com/FarMappa)",
    "Accept": "application/json",
}


class LovimeSource(BaseSource):
    SOURCE_ID    = "lovime"
    SOURCE_LABEL = "lovime.bio (api.lovime.bio JSON API)"

    def __init__(self, conn, limit=None):
        super().__init__(conn, limit)
        self.session = requests.Session()

    # ── Abstract method implementations ───────────────────────────────────────

    def fetch_listings(self) -> list[dict]:
        """POST /filter with an empty body to retrieve all producer listings."""
        print(f"[{self.SOURCE_ID}] Fetching producer list from {FILTER_URL} …")
        resp = self.session.post(FILTER_URL, json={}, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        listings = resp.json()
        print(f"[{self.SOURCE_ID}] {len(listings)} listings found", end="")
        if self.limit:
            listings = listings[: self.limit]
            print(f" (limited to {self.limit})", end="")
        print()
        return listings

    def build_record(self, raw: dict) -> tuple[dict, set[str]] | None:
        """
        Fetch the /place/{id} detail for one listing and assemble a DB record.

        raw is one element from the /filter response:
          {id, name, district, region, gps, phone, selling, specializations}
        """
        place_id    = raw.get("id")
        name        = (raw.get("name") or "").strip()
        phone       = raw.get("phone") or ""
        basic_specs = raw.get("specializations") or []

        if not name:
            return None

        # Parse GPS from the listing-level field (lat,lon string)
        gps = parse_gps(raw.get("gps", ""))
        latitude, longitude = gps if gps else (None, None)

        # Fetch full detail for description, website, email, and structured address
        detail = self._fetch_detail(place_id) if place_id else None

        description = ""
        website     = ""
        email       = ""
        address     = ""
        all_specs   = list(basic_specs)

        if detail:
            description = detail.get("description") or ""
            website     = detail.get("website") or ""
            email       = detail.get("email") or ""

            addr_obj = detail.get("address") or {}
            parts    = [addr_obj.get("street", ""), addr_obj.get("city", "")]
            address  = ", ".join(p for p in parts if p)

            # Prefer more precise GPS from detail if listing GPS was absent
            if not gps:
                gps = parse_gps(addr_obj.get("gps", ""))
                if gps:
                    latitude, longitude = gps

            # Merge specializations from both listing and detail
            all_specs += detail.get("specializations") or []
        else:
            # Rough address fallback using district + region from listing
            parts   = [raw.get("district", ""), raw.get("region", "")]
            address = ", ".join(p for p in parts if p)

        category_slugs = map_specializations(all_specs)

        record = {
            "name_cs":        name,
            "description_cs": description or None,
            "address":        address or None,
            "latitude":       latitude,
            "longitude":      longitude,
            "website":        website or None,
            "phone":          phone or None,
            "email":          email or None,
            "social_media":   json.dumps({}, ensure_ascii=False),
        }
        return record, category_slugs

    # ── Private helpers ────────────────────────────────────────────────────────

    def _fetch_detail(self, place_id: int) -> dict | None:
        """GET /place/{id} — returns full location detail. Returns None on error."""
        time.sleep(REQUEST_DELAY)
        try:
            resp = self.session.get(f"{PLACE_URL}/{place_id}", headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            print(f"  [{self.SOURCE_ID}] warn: could not fetch detail for place {place_id}: {exc}")
            return None
