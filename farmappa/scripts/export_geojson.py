"""
scripts/export_geojson.py — Export FarMappa database to GeoJSON for the web map.

Writes web/data.geojson — only locations that have GPS coordinates are exported
(locations without lat/lon cannot be placed on a map).

Usage (from project root):
    python scripts/export_geojson.py
"""

import json
import sys
from pathlib import Path

# Resolve paths relative to project root regardless of working directory
ROOT    = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "farmappa.db"
OUT_DIR = ROOT / "web"
OUT_PATH = OUT_DIR / "data.geojson"

# Add agents/ to sys.path so shared helpers are importable
sys.path.insert(0, str(ROOT / "agents"))
from shared.db import get_connection


def export():
    conn = get_connection()

    # Fetch all locations that have GPS, with their category slugs
    rows = conn.execute("""
        SELECT
            l.id,
            l.name_cs,
            l.description_cs,
            l.address,
            l.latitude,
            l.longitude,
            l.website,
            l.phone,
            l.email,
            l.social_media,
            l.verified,
            GROUP_CONCAT(c.slug, ',') AS categories
        FROM locations l
        LEFT JOIN location_categories lc ON lc.location_id = l.id
        LEFT JOIN categories c           ON c.id = lc.category_id
        WHERE l.latitude IS NOT NULL
          AND l.longitude IS NOT NULL
        GROUP BY l.id
        ORDER BY l.id
    """).fetchall()

    features = []
    for row in rows:
        # Parse social media JSON safely
        social = {}
        if row["social_media"]:
            try:
                social = json.loads(row["social_media"])
            except json.JSONDecodeError:
                pass

        categories = [c for c in (row["categories"] or "").split(",") if c]

        props = {
            "id":          row["id"],
            "name":        row["name_cs"],
            "description": row["description_cs"],
            "address":     row["address"],
            "website":     row["website"],
            "phone":       row["phone"],
            "email":       row["email"],
            "facebook":    social.get("facebook"),
            "instagram":   social.get("instagram"),
            "verified":    bool(row["verified"]),
            "categories":  categories,
        }
        # Strip None values to keep the file compact
        props = {k: v for k, v in props.items() if v is not None and v != [] and v != ""}

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]],
            },
            "properties": props,
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, separators=(",", ":"))

    conn.close()
    print(f"Exported {len(features)} locations -> {OUT_PATH}")


if __name__ == "__main__":
    export()
