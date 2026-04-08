"""
agents/shared/utils.py — Small helpers shared across all FarMappa sources.
"""

import io
import sys


def fix_utf8_stdout() -> None:
    """Force UTF-8 output on Windows terminals (which default to cp1250)."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def parse_gps(raw: str) -> tuple[float, float] | None:
    """
    Parse a "latitude,longitude" string into a (lat, lon) float tuple.
    Returns None if the string is empty or unparseable.

    Czech data sources consistently use this format, so this helper
    is worth sharing across all sources.
    """
    if not raw:
        return None
    try:
        lat_str, lon_str = raw.split(",", 1)
        return float(lat_str.strip()), float(lon_str.strip())
    except (ValueError, AttributeError):
        return None


def print_summary(stats_list: list[dict]) -> None:
    """
    Print a formatted run summary from a list of per-source stat dicts.

    Each dict must have keys: source, label, total, saved, skipped, no_cats, errors.
    """
    print("\n" + "=" * 65)
    print("SCRAPE COMPLETE — SUMMARY")
    print("=" * 65)

    grand = {"total": 0, "saved": 0, "skipped": 0, "no_cats": 0, "errors": 0}

    for s in stats_list:
        print(f"\n  Source : {s['label']}")
        print(f"  Fetched: {s['total']}  |  Saved: {s['saved']}  |  "
              f"Skipped: {s['skipped']}  |  No category: {s['no_cats']}  |  "
              f"Errors: {s['errors']}")
        for key in grand:
            grand[key] += s[key]

    if len(stats_list) > 1:
        print(f"\n  {'─' * 55}")
        print(f"  TOTAL  : Fetched {grand['total']}  |  Saved {grand['saved']}  |  "
              f"Skipped {grand['skipped']}  |  Errors {grand['errors']}")

    print("=" * 65)
