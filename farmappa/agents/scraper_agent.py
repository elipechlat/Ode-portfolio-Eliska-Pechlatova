"""
scraper_agent.py — FarMappa multi-source scraper runner

Discovers all registered data sources and runs them in sequence.

Usage (from project root):
    python agents/scraper_agent.py                      # run all sources
    python agents/scraper_agent.py --source lovime      # run one source
    python agents/scraper_agent.py --limit 10           # test: first 10 per source

Adding a new source:
    1. Create agents/sources/your_source.py subclassing BaseSource
    2. Add one import line and one entry to KNOWN_SOURCES below — done.
"""

# Put agents/ on sys.path first so that "from shared.x" and "from sources.x"
# resolve correctly when this file is run directly as a script.
import sys
from pathlib import Path

_AGENTS_DIR = str(Path(__file__).resolve().parent)
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

import argparse

from shared.db import get_connection
from shared.utils import fix_utf8_stdout, print_summary
from sources.lovime import LovimeSource
from sources.farmarske_trhy import FarmarskeTrhySource
from sources.najdisivcelare import NajdisivcélareSource

# ── Registry — add new sources here ───────────────────────────────────────────

KNOWN_SOURCES: dict[str, type] = {
    "lovime":           LovimeSource,
    "farmarske_trhy":   FarmarskeTrhySource,
    "najdisivcelare":   NajdisivcélareSource,
    # "rohlik":         RohlikSource,
}

# ── Runner ─────────────────────────────────────────────────────────────────────

def main():
    fix_utf8_stdout()

    parser = argparse.ArgumentParser(description="FarMappa multi-source scraper")
    parser.add_argument(
        "--source", nargs="+", metavar="ID",
        help=f"Source(s) to run. Choices: {', '.join(KNOWN_SOURCES)}. "
             "Defaults to all sources.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N listings per source (for testing).",
    )
    args = parser.parse_args()

    # Resolve which sources to run
    if args.source:
        unknown = set(args.source) - KNOWN_SOURCES.keys()
        if unknown:
            print(f"Error: unknown source(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(KNOWN_SOURCES)}")
            sys.exit(1)
        selected = {k: v for k, v in KNOWN_SOURCES.items() if k in args.source}
    else:
        selected = KNOWN_SOURCES

    conn      = get_connection()
    all_stats = []

    for source_cls in selected.values():
        source = source_cls(conn=conn, limit=args.limit)
        stats  = source.run()
        all_stats.append(stats)

    conn.close()
    print_summary(all_stats)


if __name__ == "__main__":
    main()
