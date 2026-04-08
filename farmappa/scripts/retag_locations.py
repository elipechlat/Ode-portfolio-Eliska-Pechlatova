"""
scripts/retag_locations.py — Apply updated category keyword rules to all existing locations.

When new categories are added to categories.py, existing locations in the DB won't
automatically get tagged because the scrapers skip them as duplicates. This script
re-runs keyword matching on every location's description text and adds any newly
matched category links that don't already exist.

Safe to run multiple times — uses INSERT OR IGNORE so nothing is double-counted.

Usage (from project root):
    python scripts/retag_locations.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agents"))

from shared.db import get_connection
from shared.categories import KEYWORD_RULES


def retag_all():
    conn = get_connection()

    # Load category slug → id mapping
    cat_id = {row[0]: row[1] for row in conn.execute("SELECT slug, id FROM categories")}

    # Fetch every location that has a description
    locations = conn.execute(
        "SELECT id, name_cs, description_cs FROM locations WHERE description_cs IS NOT NULL"
    ).fetchall()

    print(f"Re-tagging {len(locations)} locations against {len(KEYWORD_RULES)} keyword rules …\n")

    added_total = 0
    touched     = 0

    for loc in locations:
        loc_id      = loc["id"]
        description = (loc["description_cs"] or "").lower()

        # Collect every matching slug (one per keyword rule, first-match-wins per rule group).
        # Unlike map_specializations we check ALL rules against the full text so a single
        # description can match multiple new categories.
        matched: set[str] = set()
        for keyword, slug in KEYWORD_RULES:
            if keyword.lower() in description and slug in cat_id:
                matched.add(slug)

        if not matched:
            continue

        # Insert only links that are genuinely new
        added_here = 0
        for slug in matched:
            cid = cat_id[slug]
            cursor = conn.execute(
                "INSERT OR IGNORE INTO location_categories (location_id, category_id) VALUES (?,?)",
                (loc_id, cid),
            )
            if cursor.rowcount:
                added_here += 1

        if added_here:
            conn.commit()
            cats_str = ", ".join(sorted(matched))
            print(f"  [{loc_id}] {loc['name_cs'][:50]:<50}  +{added_here} ({cats_str})")
            added_total += added_here
            touched     += 1

    conn.close()
    print(f"\n{'='*60}")
    print(f"RE-TAGGING COMPLETE")
    print(f"{'='*60}")
    print(f"  Locations updated : {touched}")
    print(f"  Category links added: {added_total}")
    print(f"{'='*60}")


if __name__ == "__main__":
    retag_all()
