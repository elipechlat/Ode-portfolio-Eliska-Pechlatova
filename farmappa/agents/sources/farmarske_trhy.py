"""
agents/sources/farmarske_trhy.py — FarMappa source for trhynakulataku.cz

farmarske-trhy.cz redirects to trhynakulataku.cz (Trhy na Kulaťáku / Trhy na Andělu),
a Prague-based farmers market directory run by the same organisation.

The site has no JSON API — we scrape HTML with BeautifulSoup.

Strategy:
  1. GET /nasi-prodejci-a-farmari/ — collect all vendor page URLs
  2. GET /{vendor-slug}/           — extract name, description, website, social media
  3. Map description text to FarMappa categories; always add "farmers_market"
  4. Use fixed market GPS (vendors don't have individual farm addresses here)
"""

import json
import time

import requests
from bs4 import BeautifulSoup

from shared.base_source import BaseSource
from shared.categories import map_specializations

BASE_URL     = "https://www.trhynakulataku.cz"
LISTING_PATH = "/nasi-prodejci-a-farmari/"
REQUEST_DELAY = 0.5  # seconds between page fetches

HEADERS = {
    "User-Agent": "FarMappaBot/1.0 (open-source food map; github.com/FarMappa)",
    "Accept": "text/html,application/xhtml+xml",
}

# Navigation and structural paths that are NOT vendor pages
SKIP_PATHS = {
    "/", "/home/", "/akce-na-trzich/", "/trhy-na-kulataku/", "/pro-farmare/",
    "/seznam-farmaru-kulatak/", "/trhynakulataku/fotogalerie/", "/videa/",
    "/trhy-andel/", "/pro-farmare2/", "/seznam-farmaru-andel/",
    "/trhynaandelu/fotogalerie/", "/festival-ambasad/", "/festival-of-embassies/",
    "/embassy-festival-haag/", "/festivalambasad/fotogalerie/", "/blog/",
    "/recepty/", "/kontakt/", "/nasi-prodejci-a-farmari/",
}

# The two fixed market locations (vendors attend one or both; we default to Kulaťák)
MARKETS = {
    "kulatak": {
        "address":  "Vítězné náměstí, Praha 6 (Trhy na Kulaťáku)",
        "latitude":  50.0985,
        "longitude": 14.3863,
        "hours":    json.dumps({"sat": "8:00–14:00"}, ensure_ascii=False),
    },
    "andel": {
        "address":  "Pěší zóna Anděl, Praha 5 (Trhy na Andělu)",
        "latitude":  50.0708,
        "longitude": 14.4033,
        "hours":    json.dumps({"tue": "8:00–18:00"}, ensure_ascii=False),
    },
}

# Domains we recognise as social/platform links, not the vendor's own website
SOCIAL_DOMAINS = ("facebook.com", "instagram.com", "twitter.com", "youtube.com")
# Domains to ignore entirely when collecting external links
IGNORE_DOMAINS = ("trhynakulataku.cz", "farmarske-trhy.cz",
                  "cloudfront.net", "clvaw-cdnwnd.com", "webnode.")


class FarmarskeTrhySource(BaseSource):
    SOURCE_ID    = "farmarske_trhy"
    SOURCE_LABEL = "trhynakulataku.cz (Trhy na Kulaťáku / Trhy na Andělu) — HTML scrape"

    def __init__(self, conn, limit=None):
        super().__init__(conn, limit)
        self.session = requests.Session()

    # ── Abstract method implementations ───────────────────────────────────────

    def fetch_listings(self) -> list[dict]:
        """
        Scrape the vendor directory page to collect all vendor URLs.
        Returns a list of dicts, each with just a "url" key.
        The actual data is fetched per-vendor in build_record().
        """
        print(f"[{self.SOURCE_ID}] Fetching vendor list from {BASE_URL}{LISTING_PATH} …")
        resp = self.session.get(
            BASE_URL + LISTING_PATH, headers=HEADERS, timeout=20
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Vendor links are absolute URLs pointing back to the same domain.
        # They have images (no link text) and a single path segment.
        vendor_urls = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith(BASE_URL + "/"):
                continue
            path = href[len(BASE_URL):]
            # Keep only single-segment paths not in the skip list
            if path in SKIP_PATHS or path in seen:
                continue
            if path.count("/") != 2:   # exactly one slug between two slashes
                continue
            seen.add(path)
            vendor_urls.append({"url": href})

        print(f"[{self.SOURCE_ID}] {len(vendor_urls)} vendor pages found", end="")
        if self.limit:
            vendor_urls = vendor_urls[: self.limit]
            print(f" (limited to {self.limit})", end="")
        print()
        return vendor_urls

    def build_record(self, raw: dict) -> tuple[dict, set[str]] | None:
        """
        Fetch one vendor detail page and extract all available fields.
        raw = {"url": "https://www.trhynakulataku.cz/{slug}/"}
        """
        url = raw["url"]
        time.sleep(REQUEST_DELAY)

        resp = self.session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Name ──────────────────────────────────────────────────────────────
        h1 = soup.find("h1")
        name = h1.get_text(strip=True) if h1 else None
        if not name:
            # Fall back to page title (strip " | Trhy na Kulaťáku" suffix if present)
            name = (soup.title.string or "").split("|")[0].strip()
        if not name:
            return None   # can't identify the vendor

        # ── Description ───────────────────────────────────────────────────────
        # H2 typically holds a product tagline; first long paragraph is the body text
        h2 = soup.find("h2")
        tagline = h2.get_text(strip=True) if h2 else ""

        paragraphs = [
            p.get_text(strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 40
               and "cookies" not in p.get_text().lower()   # skip cookie-consent text
        ]
        body = paragraphs[0] if paragraphs else ""

        description = ". ".join(filter(None, [tagline, body]))

        # ── External links (website + social media) ───────────────────────────
        website   = None
        facebook  = None
        instagram = None

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if any(d in href for d in IGNORE_DOMAINS):
                continue
            if "facebook.com" in href:
                # Skip the market's own FB page (shared across all vendors)
                if "farmarsketrhy" not in href and facebook is None:
                    facebook = href
            elif "instagram.com" in href and instagram is None:
                # Skip the market's own IG account
                if "trhynakulataku" not in href and "farmarsketrhy" not in href:
                    instagram = href
            elif not any(d in href for d in SOCIAL_DOMAINS) and website is None:
                website = href

        social_media = json.dumps(
            {k: v for k, v in {"facebook": facebook, "instagram": instagram}.items() if v},
            ensure_ascii=False,
        )

        # ── Market location (default to Kulaťák) ──────────────────────────────
        # A few vendors mention "Anděl" explicitly in their page text
        page_text = soup.get_text().lower()
        market = MARKETS["andel"] if "andělu" in page_text and "kulaťáku" not in page_text \
                 else MARKETS["kulatak"]

        # ── Categories ────────────────────────────────────────────────────────
        # Map description text; always include farmers_market since these are market vendors
        category_slugs = map_specializations([tagline, body])
        category_slugs.add("farmers_market")

        record = {
            "name_cs":        name,
            "description_cs": description or None,
            "address":        market["address"],
            "latitude":       market["latitude"],
            "longitude":      market["longitude"],
            "website":        website,
            "phone":          None,    # only a shared market phone exists; not stored per vendor
            "email":          None,
            "social_media":   social_media,
        }
        return record, category_slugs
