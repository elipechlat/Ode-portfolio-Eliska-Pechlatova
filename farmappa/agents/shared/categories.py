"""
agents/shared/categories.py — Category keyword mapping for FarMappa.

This is the single source of truth for mapping raw product/specialization
strings (typically Czech) to FarMappa category slugs.

To extend:
  1. Add a new slug to database/schema.sql (INSERT OR IGNORE into categories)
  2. Add keyword rules here — no source file needs to be touched.
"""

# Each rule is (keyword_substring, farmappa_slug).
# Matching is case-insensitive substring search.
# Rules are evaluated in order; the FIRST match for a given string wins,
# so put more-specific rules before broader ones (e.g. "kozí" before "mléko").

KEYWORD_RULES: list[tuple[str, str]] = [
    # ── Beekeeper / honey ────────────────────────────────────────────────────
    ("včel",            "beekeeper"),
    ("med",             "beekeeper"),

    # ── Goat milk (before generic dairy) ────────────────────────────────────
    ("kozí",            "goat_milk"),

    # ── Sheep milk (before generic dairy) ───────────────────────────────────
    ("ovčí",            "sheep_milk"),
    ("ovce",            "sheep_milk"),

    # ── Dairy catch-all ──────────────────────────────────────────────────────
    ("mléko",           "dairy"),
    ("sýr",             "dairy"),
    ("máslo",           "dairy"),
    ("jogurt",          "dairy"),
    ("tvaroh",          "dairy"),
    ("mlékár",          "dairy"),
    ("kefír",           "dairy"),
    ("skyr",            "dairy"),

    # ── Organic eggs ─────────────────────────────────────────────────────────
    ("vejce",           "organic_eggs"),

    # ── Organic meat ─────────────────────────────────────────────────────────
    ("maso",            "organic_meat"),
    ("hovězí",          "organic_meat"),
    ("vepřov",          "organic_meat"),
    ("drůbež",          "organic_meat"),
    ("kuřec",           "organic_meat"),
    ("jehněč",          "organic_meat"),
    ("telecí",          "organic_meat"),
    ("králík",          "organic_meat"),
    ("salám",           "organic_meat"),
    ("klobás",          "organic_meat"),
    ("uzenin",          "organic_meat"),

    # ── Potatoes ─────────────────────────────────────────────────────────────
    ("brambor",         "potatoes"),

    # ── Vegetables ───────────────────────────────────────────────────────────
    ("zelenin",         "vegetables"),

    # ── Fruits ───────────────────────────────────────────────────────────────
    ("ovoce",           "fruits"),
    ("ovoc",            "fruits"),
    ("jablk",           "fruits"),
    ("hrušk",           "fruits"),
    ("třešn",           "fruits"),
    ("meruňk",          "fruits"),
    ("švestk",          "fruits"),
    ("jahod",           "fruits"),
    ("malin",           "fruits"),
    ("rybíz",           "fruits"),
    ("borůvk",          "fruits"),
    ("angrešt",         "fruits"),
    ("šípk",            "fruits"),

    # ── Organic grains ───────────────────────────────────────────────────────
    ("obilov",          "organic_grains"),
    ("pšenic",          "organic_grains"),
    ("žito",            "organic_grains"),
    ("ječmen",          "organic_grains"),
    ("oves",            "organic_grains"),
    ("kukuřic",         "organic_grains"),
    ("pohank",          "organic_grains"),
    ("proso",           "organic_grains"),
    ("špalda",          "organic_grains"),
    ("mouka",           "organic_grains"),
    ("pekár",           "organic_grains"),
    ("chléb",           "organic_grains"),
    ("pečiv",           "organic_grains"),

    # ── Self-picking ─────────────────────────────────────────────────────────
    ("samosběr",        "self_picking"),
    ("samo-sbě",        "self_picking"),
    ("u-pick",          "self_picking"),

    # ── Farmers' market / direct sales points ────────────────────────────────
    ("farmářský trh",   "farmers_market"),
    ("prodejní míst",   "farmers_market"),
    ("farm shop",       "farmers_market"),

    # ── Vineyard / organic wine ───────────────────────────────────────────────
    ("vinic",           "vineyard"),    # vinice, vinický
    ("vinař",           "vineyard"),    # vinařství, vinař
    ("réva",            "vineyard"),    # réva vinná
    ("hrozny",          "vineyard"),    # grapes

    # ── Organic herbs ─────────────────────────────────────────────────────────
    ("bylink",          "organic_herbs"),   # bylinky, bylinkový

    # ── Flower farms ──────────────────────────────────────────────────────────
    ("levandule",       "flower_farm"),
    ("pivoňk",          "flower_farm"),
    ("tulipán",         "flower_farm"),
    ("kytice",          "flower_farm"),

    # ── CSA / bedýnkové farmy ─────────────────────────────────────────────────
    ("bedýnk",          "csa"),             # bedýnky, bedýnková
    ("kpz",             "csa"),             # komunitou podporované zemědělství
    ("komunitou podpor","csa"),

    # ── Organic nurseries ─────────────────────────────────────────────────────
    ("školkař",         "nursery"),
    ("ovocná školka",   "nursery"),

    # ── Community farms ───────────────────────────────────────────────────────
    ("komunitní farma", "community_farm"),
]


def map_specializations(specializations: list[dict | str]) -> set[str]:
    """
    Convert a list of specialization objects (or plain strings) to a set
    of FarMappa category slugs using KEYWORD_RULES above.

    Accepts both:
      - dicts with a "name" key  — as returned by api.lovime.bio
      - plain strings            — for sources that already extract text

    Each specialization is matched against rules in order; first match wins.
    A single specialization can produce only one slug.
    """
    matched_slugs: set[str] = set()
    for spec in specializations:
        name = (spec.get("name", "") if isinstance(spec, dict) else spec).lower()
        for keyword, slug in KEYWORD_RULES:
            if keyword in name:
                matched_slugs.add(slug)
                break
    return matched_slugs
