"""
agents/sources/najdisivcelare.py — FarMappa source for najdisivcelare.cz

"Najdi si včelaře" is a Czech beekeeper directory (~305 listings) organised
by region and district. It runs on a PrestaShop template; there is no API —
we scrape HTML with BeautifulSoup.

Strategy:
  1. GET homepage — collect all regional / district category links
  2. GET each category page — collect unique beekeeper detail URLs (.html)
  3. GET each detail page — extract name, description, address, phone, email,
     website using regex patterns applied to the free-text product description
  4. Assign category "beekeeper" to every record (the site is honey-only)
"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

from shared.base_source import BaseSource

BASE_URL      = "https://www.najdisivcelare.cz"
REQUEST_DELAY = 0.5   # seconds between page fetches — be polite

HEADERS = {
    "User-Agent": "FarMappaBot/1.0 (open-source food map; github.com/FarMappa)",
    "Accept": "text/html,application/xhtml+xml",
}

# Regex patterns for contact fields embedded in free-text descriptions
_RE_PHONE   = re.compile(
    r"""(?<!\d)                   # not preceded by a digit
        (\+?420[\s\-]?)?          # optional country code
        [67]\d{2}[\s\-]?\d{3}[\s\-]?\d{3}  # mobile (6xx / 7xx) 9 digits
        |(?<!\d)\+?420[\s\-]?[2-5]\d{8}    # landline with country code
        |(?<!\d)[2-5]\d{7,8}               # landline without country code
    """,
    re.VERBOSE,
)
_RE_EMAIL   = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_RE_POSTAL  = re.compile(r"\d{3}\s?\d{2}")   # Czech 5-digit postal code


class NajdisivcélareSource(BaseSource):
    SOURCE_ID    = "najdisivcelare"
    SOURCE_LABEL = "najdisivcelare.cz (HTML scrape)"

    def __init__(self, conn, limit=None):
        super().__init__(conn, limit)
        self.session = requests.Session()

    # ── Abstract method implementations ───────────────────────────────────────

    def fetch_listings(self) -> list[dict]:
        """
        Two-pass link collection:
          Pass 1 — homepage → all category page URLs (regional + district)
          Pass 2 — each category page → all beekeeper detail URLs (.html)

        Returns a list of {"url": detail_url} dicts, de-duplicated.
        """
        print(f"[{self.SOURCE_ID}] Fetching category links from {BASE_URL} …")
        category_urls = self._collect_category_urls()
        print(f"[{self.SOURCE_ID}] {len(category_urls)} category pages to scan")

        detail_urls: set[str] = set()
        for cat_url in category_urls:
            new = self._collect_detail_urls(cat_url)
            detail_urls.update(new)
            time.sleep(REQUEST_DELAY)

        listings = [{"url": u} for u in sorted(detail_urls)]
        print(f"[{self.SOURCE_ID}] {len(listings)} unique beekeeper detail pages found", end="")
        if self.limit:
            listings = listings[: self.limit]
            print(f" (limited to {self.limit})", end="")
        print()
        return listings

    def build_record(self, raw: dict) -> tuple[dict, set[str]] | None:
        """
        Parse one beekeeper detail page.
        raw = {"url": "https://www.najdisivcelare.cz/{category}/{id}-{name}.html"}
        """
        url = raw["url"]
        time.sleep(REQUEST_DELAY)

        try:
            resp = self.session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  [{self.SOURCE_ID}] warn: could not fetch {url}: {exc}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # ── Name ──────────────────────────────────────────────────────────────
        h1 = soup.find("h1", attrs={"itemprop": "name"}) or soup.find("h1")
        name = h1.get_text(strip=True) if h1 else None
        if not name:
            title = soup.find("title")
            name = title.get_text(strip=True).split(" - ")[0].strip() if title else None
        if not name:
            return None

        # ── Description text block ────────────────────────────────────────────
        # PrestaShop stores the long description in #description or .product-description
        desc_div = (
            soup.find("div", id="description")
            or soup.find("div", class_="product-description")
            or soup.find("div", attrs={"itemprop": "description"})
        )
        raw_text = desc_div.get_text("\n", strip=True) if desc_div else ""

        # Fallback: concatenate all non-trivial paragraphs in main content
        if not raw_text:
            paragraphs = [
                p.get_text(strip=True)
                for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 20
            ]
            raw_text = "\n".join(paragraphs)

        # ── Contact field extraction from free text ────────────────────────────
        phone = self._extract_phone(raw_text)
        email = self._extract_email(raw_text)

        # ── External website links ─────────────────────────────────────────────
        website = self._extract_website(soup, url)

        # ── Address: look for postal-code pattern in text ─────────────────────
        address = self._extract_address(raw_text, soup)

        # ── Clean description (remove contact lines) ──────────────────────────
        description = self._clean_description(raw_text)

        record = {
            "name_cs":        name,
            "description_cs": description or None,
            "address":        address or None,
            "latitude":       None,   # site provides no GPS data
            "longitude":      None,
            "website":        website or None,
            "phone":          phone or None,
            "email":          email or None,
            "social_media":   json.dumps({}, ensure_ascii=False),
        }
        return record, {"beekeeper"}

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_soup(self, url: str) -> BeautifulSoup | None:
        """Fetch URL and return BeautifulSoup, or None on error."""
        try:
            resp = self.session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            print(f"  [{self.SOURCE_ID}] warn: {url}: {exc}")
            return None

    def _collect_category_urls(self) -> list[str]:
        """Scrape homepage and return all regional/district category page URLs."""
        soup = self._get_soup(BASE_URL + "/")
        if not soup:
            return []

        seen: set[str] = set()
        urls: list[str] = []
        # Category URLs match: /{digits}-prodej-medu-{slug}  (no .html suffix)
        pattern = re.compile(r"^/\d+-[a-z]")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Normalise to absolute URL
            if href.startswith("/"):
                href = BASE_URL + href
            if not href.startswith(BASE_URL):
                continue
            path = href[len(BASE_URL):]
            if pattern.match(path) and ".html" not in path and href not in seen:
                seen.add(href)
                urls.append(href)
        return urls

    def _collect_detail_urls(self, category_url: str) -> set[str]:
        """Return all beekeeper .html detail URLs found on one category page."""
        soup = self._get_soup(category_url)
        if not soup:
            return set()

        urls: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = BASE_URL + href
            if href.startswith(BASE_URL) and href.endswith(".html"):
                urls.add(href)
        return urls

    def _extract_phone(self, text: str) -> str:
        """Return first phone number found in free text, normalised."""
        m = _RE_PHONE.search(text)
        if not m:
            return ""
        # Strip internal whitespace/dashes for a clean number
        return re.sub(r"[\s\-]", "", m.group(0))

    def _extract_email(self, text: str) -> str:
        """Return first e-mail address found in free text."""
        m = _RE_EMAIL.search(text)
        return m.group(0) if m else ""

    def _extract_website(self, soup: BeautifulSoup, page_url: str) -> str:
        """
        Find the beekeeper's own website — an external link that is not
        the directory itself, not social media, and not a mailto: link.
        """
        ignore = ("najdisivcelare.cz", "facebook.com", "instagram.com",
                  "twitter.com", "youtube.com", "mailto:")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href.startswith("http"):
                continue
            if any(d in href for d in ignore):
                continue
            return href
        return ""

    def _extract_address(self, text: str, soup: BeautifulSoup) -> str:
        """
        Try to pull an address from the description text.
        Looks for lines containing a Czech postal code (e.g. "273 06").
        Falls back to breadcrumb region text if nothing found.
        """
        for line in text.splitlines():
            if _RE_POSTAL.search(line):
                return line.strip()

        # Fallback: use breadcrumb category text as a rough location
        breadcrumb = soup.find("ol", class_="breadcrumb") or soup.find("div", id="breadcrumb")
        if breadcrumb:
            crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
            # Skip "Home" equivalent (first crumb) and the page name (last)
            location_crumbs = [c for c in crumbs[1:] if c]
            if location_crumbs:
                return ", ".join(location_crumbs)

        return ""

    def _clean_description(self, text: str) -> str:
        """
        Remove lines that are just contact data (phone, email, URL patterns)
        and return the remainder joined as a single paragraph.
        """
        keep = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if _RE_PHONE.search(stripped) and len(stripped) < 30:
                continue
            if _RE_EMAIL.search(stripped) and "@" in stripped and len(stripped) < 60:
                continue
            if re.match(r"https?://", stripped):
                continue
            keep.append(stripped)
        return " ".join(keep)
