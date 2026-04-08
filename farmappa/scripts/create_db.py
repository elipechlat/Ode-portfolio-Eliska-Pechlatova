"""
create_db.py — Initialize the FarMappa SQLite database and insert one example farm.

Usage:
    python scripts/create_db.py
"""

import io
import json
import sqlite3
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Paths ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "farmappa.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert_location(conn: sqlite3.Connection, location: dict) -> int:
    """Insert a location record and return its new id."""
    sql = """
        INSERT INTO locations (
            name_cs, name_en,
            description_cs, description_en,
            address, latitude, longitude,
            website, phone, email,
            opening_hours, social_media,
            verified
        ) VALUES (
            :name_cs, :name_en,
            :description_cs, :description_en,
            :address, :latitude, :longitude,
            :website, :phone, :email,
            :opening_hours, :social_media,
            :verified
        )
    """
    cursor = conn.execute(sql, location)
    return cursor.lastrowid


def attach_categories(conn: sqlite3.Connection, location_id: int, slugs: list[str]):
    """Link a location to one or more category slugs."""
    for slug in slugs:
        row = conn.execute("SELECT id FROM categories WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise ValueError(f"Unknown category slug: '{slug}'")
        conn.execute(
            "INSERT OR IGNORE INTO location_categories (location_id, category_id) VALUES (?, ?)",
            (location_id, row["id"]),
        )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Creating database at: {DB_PATH}")
    conn = get_connection()

    # Apply schema (idempotent — uses CREATE IF NOT EXISTS)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    print("Schema applied.")

    # ── Example farm ──────────────────────────────────────────────────────────
    example_farm = {
        "name_cs": "Farma Zelený kopec",
        "name_en": "Green Hill Farm",
        "description_cs": (
            "Rodinná farma na jižní Moravě specializující se na bio zeleninu, "
            "bio vejce a čerstvý med. Prodej přímo ze dvora nebo na farmářském trhu."
        ),
        "description_en": (
            "A family farm in South Moravia specialising in organic vegetables, "
            "organic eggs, and fresh honey. Direct farm sales and farmers' market."
        ),
        "address": "Kopecká 12, 691 01 Moravský Žižkov, Czech Republic",
        "latitude": 48.8312,
        "longitude": 17.0851,
        "website": "https://www.farmazelenykopec.cz",
        "phone": "+420 777 123 456",
        "email": "info@farmazelenykopec.cz",
        "opening_hours": json.dumps({
            "tue": "9:00–17:00",
            "thu": "9:00–17:00",
            "sat": "8:00–12:00",
            "note_cs": "Mimo uvedenou dobu po předchozí domluvě.",
            "note_en": "Outside listed hours by appointment.",
        }, ensure_ascii=False),
        "social_media": json.dumps({
            "facebook": "https://www.facebook.com/farmazelenykopec",
            "instagram": "https://www.instagram.com/farmazelenykopec",
        }, ensure_ascii=False),
        "verified": 1,
    }

    # Categories this farm belongs to
    farm_categories = ["vegetables", "organic_eggs", "beekeeper", "farmers_market"]

    with conn:
        loc_id = insert_location(conn, example_farm)
        attach_categories(conn, loc_id, farm_categories)

    print(f"Inserted example farm with id={loc_id}, categories: {farm_categories}")

    # ── Verify by reading back ─────────────────────────────────────────────────
    row = conn.execute("SELECT * FROM locations WHERE id = ?", (loc_id,)).fetchone()
    cats = conn.execute(
        """
        SELECT c.slug, c.name_cs, c.name_en
        FROM location_categories lc
        JOIN categories c ON c.id = lc.category_id
        WHERE lc.location_id = ?
        """,
        (loc_id,),
    ).fetchall()

    print("\n── Inserted location ──────────────────────────────")
    print(f"  name_cs  : {row['name_cs']}")
    print(f"  name_en  : {row['name_en']}")
    print(f"  address  : {row['address']}")
    print(f"  coords   : ({row['latitude']}, {row['longitude']})")
    print(f"  verified : {'yes' if row['verified'] else 'no'}")
    print(f"  categories ({len(cats)}):")
    for c in cats:
        print(f"    [{c['slug']}]  {c['name_cs']} / {c['name_en']}")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
