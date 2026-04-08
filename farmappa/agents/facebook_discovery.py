"""
agents/facebook_discovery.py — FarMappa Facebook Page discovery agent

Uses the Facebook Graph API /pages/search endpoint to find Czech agricultural
producers (farms, beekeepers, markets, etc.) and imports them into the DB.

The /pages/search endpoint requires one of:
  • Page Public Metadata Access feature (requires Meta App Review for production)
  • A User Access Token with pages_read_engagement permission

QUICKEST SETUP (development / testing):
  1. Go to https://developers.facebook.com/tools/explorer/
  2. Select your App, click "Generate Access Token"
  3. Add permission: pages_read_engagement
  4. Copy the token and add to .env:
       FACEBOOK_APP_ID=...
       FACEBOOK_APP_SECRET=...
       FACEBOOK_USER_TOKEN=EAAxxxxx...   ← paste here
  5. Run:  python agents/facebook_discovery.py

FOR PRODUCTION (no token expiry):
  1. Submit your app for App Review and request "Page Public Metadata Access"
  2. Once approved, remove FACEBOOK_USER_TOKEN from .env — the app token works automatically
"""

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
# Allow "from shared.x" imports regardless of working directory
_AGENTS_DIR = str(Path(__file__).resolve().parent)
_ROOT_DIR   = str(Path(__file__).resolve().parent.parent)
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

from shared.db import get_connection, insert_location_with_categories, location_exists
from shared.categories import map_specializations
from shared.utils import fix_utf8_stdout

# ── Load credentials ──────────────────────────────────────────────────────────
load_dotenv(Path(_ROOT_DIR) / ".env")

APP_ID       = os.getenv("FACEBOOK_APP_ID", "")
APP_SECRET   = os.getenv("FACEBOOK_APP_SECRET", "")
USER_TOKEN   = os.getenv("FACEBOOK_USER_TOKEN", "")

# Prefer a User Access Token (has pages_read_engagement by default in Graph Explorer).
# Fall back to the App Access Token (works only after Page Public Metadata Access is approved).
ACCESS_TOKEN = USER_TOKEN if USER_TOKEN else f"{APP_ID}|{APP_SECRET}"

# ── Graph API constants ───────────────────────────────────────────────────────
GRAPH_BASE   = "https://graph.facebook.com/v19.0"
SEARCH_URL   = f"{GRAPH_BASE}/pages/search"
PAGE_FIELDS  = ",".join([
    "id", "name", "about", "description",
    "location", "phone", "website", "emails",
    "category", "fan_count", "link",
])
MAX_RESULTS_PER_QUERY = 200   # hard cap per search term (Graph API pages at 25)
REQUEST_DELAY         = 1.0   # seconds between API calls — stay well inside rate limits

# ── Czech search terms ────────────────────────────────────────────────────────
SEARCH_TERMS = [
    "bio farma",
    "farmářský trh",
    "včelař med",
    "bio zelenina",
    "bio mléko",
    "samosběr",
    "bio vejce",
    "bio maso",
    "ovčí mléko",
    "kozí mléko",
    "biofarm",
    "farma Czech",
]

HEADERS = {
    "User-Agent": "FarMappaBot/1.0 (open-source food map; github.com/FarMappa)",
}


# ── Graph API helpers ─────────────────────────────────────────────────────────

def search_pages(session: requests.Session, query: str) -> list[dict]:
    """
    Search for Facebook Pages matching *query*, filtered to Czech Republic.
    Follows pagination until MAX_RESULTS_PER_QUERY is reached or results end.
    Returns a list of raw page dicts from the API.
    """
    params = {
        "q":            query,
        "type":         "page",
        "fields":       PAGE_FIELDS,
        "access_token": ACCESS_TOKEN,
        "limit":        25,
    }
    pages: list[dict] = []
    url = SEARCH_URL

    while url and len(pages) < MAX_RESULTS_PER_QUERY:
        try:
            resp = session.get(url, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  [facebook] API error for '{query}': {exc}")
            break

        data = resp.json()

        # Surface any API-level error messages
        if "error" in data:
            err = data["error"]
            msg = err.get("message", "")
            print(f"  [facebook] Graph API error (code {err.get('code')}): {msg}")
            if "Page Public" in msg or "pages_read_engagement" in msg:
                print(
                    "  → Your app needs a User Access Token with pages_read_engagement.\n"
                    "  → Get one at https://developers.facebook.com/tools/explorer/\n"
                    "  → Add as FACEBOOK_USER_TOKEN=... in .env"
                )
            break

        batch = data.get("data", [])
        # Filter to Czech Republic only
        cz_batch = [p for p in batch if _is_czech(p)]
        pages.extend(cz_batch)

        # Follow next-page cursor
        paging = data.get("paging", {})
        next_url = paging.get("next")
        if next_url and len(pages) < MAX_RESULTS_PER_QUERY:
            url    = next_url
            params = {}          # cursor URL already contains all params
            time.sleep(REQUEST_DELAY)
        else:
            break

    return pages


def _is_czech(page: dict) -> bool:
    """Return True if the page location is in the Czech Republic."""
    loc = page.get("location") or {}
    country_code = (loc.get("country_code") or "").upper()
    country      = (loc.get("country") or "").lower()
    if country_code == "CZ":
        return True
    if "czech" in country or "česk" in country:
        return True
    # Pages with no location are not geo-filtered out here — they'll be stored
    # without GPS and the operator can review manually. To be stricter, return
    # False for pages without location data.
    return False


# ── Record builder ────────────────────────────────────────────────────────────

def build_record(page: dict) -> tuple[dict, set[str]] | None:
    """Convert one raw Graph API page dict to a DB record + category slugs."""
    name = (page.get("name") or "").strip()
    if not name:
        return None

    loc  = page.get("location") or {}
    lat  = loc.get("latitude")
    lon  = loc.get("longitude")

    # Build a human-readable address from location fields
    address_parts = [
        loc.get("street", ""),
        loc.get("city", ""),
        loc.get("zip", ""),
        loc.get("country", ""),
    ]
    address = ", ".join(p for p in address_parts if p) or None

    about       = (page.get("about")       or "").strip()
    description = (page.get("description") or "").strip()
    # Prefer 'description' (longer), fall back to 'about'
    full_desc   = description or about or None

    website = (page.get("website") or "").strip() or None
    phone   = (page.get("phone")   or "").strip() or None

    emails      = page.get("emails") or []
    email       = emails[0] if emails else None

    fb_link     = page.get("link", "")
    social_media = json.dumps(
        {"facebook": fb_link} if fb_link else {},
        ensure_ascii=False,
    )

    # Category mapping: use page's FB category + description text
    fb_category = page.get("category") or ""
    text_for_cats = " ".join(filter(None, [fb_category, about, description]))
    category_slugs = map_specializations([text_for_cats])

    record = {
        "name_cs":        name,
        "description_cs": full_desc,
        "address":        address,
        "latitude":       lat,
        "longitude":      lon,
        "website":        website,
        "phone":          phone,
        "email":          email,
        "social_media":   social_media,
    }
    return record, category_slugs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    fix_utf8_stdout()

    # Validate credentials before hitting the API
    if not APP_ID or APP_ID == "your_app_id_here":
        print("Error: FACEBOOK_APP_ID not set. Edit .env at the project root.")
        sys.exit(1)
    if not APP_SECRET or APP_SECRET == "your_app_secret_here":
        print("Error: FACEBOOK_APP_SECRET not set. Edit .env at the project root.")
        sys.exit(1)
    if not USER_TOKEN:
        print(
            "Note: No FACEBOOK_USER_TOKEN found. Using App Access Token.\n"
            "      If you get permission errors, generate a token at:\n"
            "      https://developers.facebook.com/tools/explorer/\n"
            "      (add pages_read_engagement, paste as FACEBOOK_USER_TOKEN in .env)\n"
        )

    conn    = get_connection()
    session = requests.Session()

    per_term_stats: dict[str, dict] = {}
    grand_saved   = 0
    grand_skipped = 0
    grand_errors  = 0

    for term in SEARCH_TERMS:
        print(f"\n[facebook] Searching: '{term}' …")
        pages = search_pages(session, term)
        print(f"[facebook]   → {len(pages)} Czech pages found")

        term_saved = term_skipped = term_errors = 0

        for page in pages:
            result = build_record(page)
            if result is None:
                term_errors += 1
                continue

            record, category_slugs = result
            name_cs   = record["name_cs"]
            latitude  = record["latitude"]
            longitude = record["longitude"]

            if location_exists(conn, name_cs, latitude, longitude):
                print(f"  skipped (duplicate): {name_cs}")
                term_skipped += 1
                continue

            try:
                loc_id = insert_location_with_categories(conn, record, category_slugs)
                cats   = ", ".join(sorted(category_slugs)) if category_slugs else "—"
                print(f"  saved (id={loc_id}): {name_cs}  [{cats}]")
                term_saved += 1
            except Exception as exc:
                print(f"  DB error for '{name_cs}': {exc}")
                term_errors += 1

        per_term_stats[term] = {
            "found":   len(pages),
            "saved":   term_saved,
            "skipped": term_skipped,
            "errors":  term_errors,
        }
        grand_saved   += term_saved
        grand_skipped += term_skipped
        grand_errors  += term_errors

        time.sleep(REQUEST_DELAY)

    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("FACEBOOK DISCOVERY — SUMMARY")
    print("=" * 65)
    print(f"  {'Search term':<25}  {'Found':>5}  {'Saved':>5}  {'Skipped':>7}  {'Errors':>6}")
    print(f"  {'-'*25}  {'-'*5}  {'-'*5}  {'-'*7}  {'-'*6}")
    for term, s in per_term_stats.items():
        print(f"  {term:<25}  {s['found']:>5}  {s['saved']:>5}  {s['skipped']:>7}  {s['errors']:>6}")
    print(f"  {'─'*55}")
    print(f"  {'TOTAL':<25}  {'':>5}  {grand_saved:>5}  {grand_skipped:>7}  {grand_errors:>6}")
    print("=" * 65)


if __name__ == "__main__":
    main()
