"""
agents/shared/db.py — SQLite helpers shared across all FarMappa sources.

DB_PATH is resolved relative to this file's location so the database is
always found regardless of the working directory the runner is called from.
"""

import sqlite3
from pathlib import Path

# agents/shared/db.py  →  .parent = shared/  →  .parent = agents/  →  .parent = project root
ROOT   = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "database" / "farmappa.db"


def get_connection() -> sqlite3.Connection:
    """Open and return a SQLite connection with foreign keys enabled."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run 'python scripts/create_db.py' first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def location_exists(
    conn: sqlite3.Connection,
    name_cs: str,
    latitude: float | None,
    longitude: float | None,
) -> bool:
    """
    Return True if a location with the same name and GPS is already in the DB.

    When GPS is available, matches on name + coordinates within ~10 m.
    Falls back to name-only when GPS is absent.
    """
    if latitude is None or longitude is None:
        row = conn.execute(
            "SELECT 1 FROM locations WHERE name_cs = ? LIMIT 1", (name_cs,)
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT 1 FROM locations
               WHERE name_cs = ?
                 AND ABS(latitude  - ?) < 0.0001
                 AND ABS(longitude - ?) < 0.0001
               LIMIT 1""",
            (name_cs, latitude, longitude),
        ).fetchone()
    return row is not None


def insert_location_with_categories(
    conn: sqlite3.Connection,
    record: dict,
    category_slugs: set[str],
) -> int:
    """
    Insert a location row and link it to its categories in one transaction.

    ``record`` must contain keys matching locations table columns:
        name_cs, description_cs, address, latitude, longitude,
        website, phone, email, social_media

    Returns the new location id.
    """
    sql = """
        INSERT INTO locations (
            name_cs, description_cs,
            address, latitude, longitude,
            website, phone, email,
            social_media, verified
        ) VALUES (
            :name_cs, :description_cs,
            :address, :latitude, :longitude,
            :website, :phone, :email,
            :social_media, 0
        )
    """
    with conn:
        cursor = conn.execute(sql, record)
        loc_id = cursor.lastrowid

        for slug in category_slugs:
            cat = conn.execute(
                "SELECT id FROM categories WHERE slug = ?", (slug,)
            ).fetchone()
            if cat:
                conn.execute(
                    "INSERT OR IGNORE INTO location_categories "
                    "(location_id, category_id) VALUES (?, ?)",
                    (loc_id, cat["id"]),
                )
    return loc_id
