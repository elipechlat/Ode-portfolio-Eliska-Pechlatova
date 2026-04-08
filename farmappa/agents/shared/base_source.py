"""
agents/shared/base_source.py — Abstract base class for all FarMappa data sources.

Every source (lovime.py, farmarske_trhy.py, …) must subclass BaseSource and
implement fetch_listings() and build_record(). The run() loop is inherited.
"""

import sqlite3
from abc import ABC, abstractmethod

from shared.db import insert_location_with_categories, location_exists


class BaseSource(ABC):
    """
    Contract every FarMappa data source must fulfill.

    Responsibilities of a source:
      - fetch its own raw data (HTTP / HTML / file — anything)
      - convert each raw record to a canonical (location_dict, category_slugs) pair
      - delegate duplicate-checking and DB writes to shared helpers

    Sources must NOT open/close the DB connection or define keyword-mapping
    tables — those live in shared/db.py and shared/categories.py respectively.
    """

    # Short machine-readable identifier, e.g. "lovime". Used for --source filtering.
    SOURCE_ID: str = ""

    # Human-readable label shown in the summary, e.g. "lovime.bio (JSON API)".
    SOURCE_LABEL: str = ""

    def __init__(self, conn: sqlite3.Connection, limit: int | None = None):
        """
        Parameters
        ----------
        conn:
            Open SQLite connection provided by the runner. Sources do not
            open or close it themselves.
        limit:
            If set, process at most this many records (for --limit N test runs).
        """
        self.conn  = conn
        self.limit = limit

    @abstractmethod
    def fetch_listings(self) -> list[dict]:
        """
        Retrieve all raw listing records from the source.

        Returns a list of dicts in whatever shape the source produces.
        Must apply self.limit if set (slice the list before returning).
        Data transformation belongs in build_record(), not here.
        """
        ...

    @abstractmethod
    def build_record(self, raw: dict) -> tuple[dict, set[str]] | None:
        """
        Convert one raw listing dict into a DB-ready (record, category_slugs) pair.

        Parameters
        ----------
        raw:
            One element from the list returned by fetch_listings().

        Returns
        -------
        A 2-tuple of:
          record       — dict with keys: name_cs, description_cs, address,
                         latitude, longitude, website, phone, email, social_media
          category_slugs — set of FarMappa category slug strings

        Return None to skip a malformed record (counted as an error).

        Sources with native category tags can return slugs directly.
        Sources with free-text product descriptions should call
        map_specializations() from shared/categories.py.
        """
        ...

    def run(self) -> dict:
        """
        Orchestrate the full scrape for this source.

        Calls fetch_listings(), iterates, calls build_record() per item,
        checks for duplicates, inserts new records, and returns a stats dict:

            {
                "source":  str,   # SOURCE_ID
                "label":   str,   # SOURCE_LABEL
                "total":   int,   # listings fetched
                "saved":   int,
                "skipped": int,   # duplicates already in DB
                "no_cats": int,   # saved but zero categories matched
                "errors":  int,
            }

        Override only if the source needs non-standard pagination or
        session management that doesn't fit the fetch → iterate model.
        """
        stats = {
            "source":  self.SOURCE_ID,
            "label":   self.SOURCE_LABEL,
            "total":   0,
            "saved":   0,
            "skipped": 0,
            "no_cats": 0,
            "errors":  0,
        }

        listings = self.fetch_listings()
        stats["total"] = len(listings)

        for i, raw in enumerate(listings, start=1):
            result = None
            try:
                result = self.build_record(raw)
            except Exception as exc:
                print(f"  [{self.SOURCE_ID}] [{i}/{stats['total']}] build_record error: {exc}")
                stats["errors"] += 1
                continue

            if result is None:
                stats["errors"] += 1
                continue

            record, category_slugs = result
            name_cs   = record.get("name_cs", "")
            latitude  = record.get("latitude")
            longitude = record.get("longitude")

            if location_exists(self.conn, name_cs, latitude, longitude):
                print(f"  [{self.SOURCE_ID}] [{i}/{stats['total']}] {name_cs} — skipped (duplicate)")
                stats["skipped"] += 1
                continue

            if not category_slugs:
                stats["no_cats"] += 1

            try:
                loc_id = insert_location_with_categories(self.conn, record, category_slugs)
                cats   = ", ".join(sorted(category_slugs)) if category_slugs else "—"
                print(f"  [{self.SOURCE_ID}] [{i}/{stats['total']}] {name_cs} "
                      f"— saved (id={loc_id}, cats: {cats})")
                stats["saved"] += 1
            except Exception as exc:
                print(f"  [{self.SOURCE_ID}] [{i}/{stats['total']}] {name_cs} — DB error: {exc}")
                stats["errors"] += 1

        return stats
