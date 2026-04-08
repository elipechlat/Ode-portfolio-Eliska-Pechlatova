-- FarMappa Database Schema
-- SQLite

PRAGMA foreign_keys = ON;

-- ─── Categories ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT NOT NULL UNIQUE,   -- machine-readable key, e.g. "organic_eggs"
    name_cs     TEXT NOT NULL,          -- Czech name
    name_en     TEXT NOT NULL           -- English name
);

-- Seed data for all supported categories
INSERT OR IGNORE INTO categories (slug, name_cs, name_en) VALUES
    ('farmers_market',   'Farmářský trh',                    'Farmers'' market'),
    ('beekeeper',        'Včelař',                           'Beekeeper'),
    ('goat_milk',        'Bio kozí mléko a produkty',        'Organic goat milk and products'),
    ('organic_meat',     'Bio maso',                         'Organic meat'),
    ('potatoes',         'Brambory',                         'Potatoes'),
    ('vegetables',       'Zelenina',                         'Vegetables'),
    ('fruits',           'Ovoce',                            'Fruits'),
    ('self_picking',     'Samosběr',                         'Self-picking (Samosběr)'),
    ('organic_grains',   'Bio obiloviny',                    'Organic grains'),
    ('dairy',            'Mléčné výrobky (bio/pastevní/travní)', 'Dairy and dairy products (organic/pasture-raised/grassfed)'),
    ('organic_eggs',     'Bio vejce',                        'Organic eggs'),
    ('sheep_milk',       'Ovčí mléko a produkty',            'Sheep''s milk and products'),
    ('organic_herbs',   'Bio bylinky',                      'Organic herbs'),
    ('vineyard',        'Vinohrady a bio víno',              'Vineyards and organic wine'),
    ('csa',             'Bedýnkové / komunitní zemědělství', 'Community supported agriculture (CSA)'),
    ('nursery',         'Bio školky a sazenice',             'Organic nurseries and seedlings'),
    ('flower_farm',     'Květinové farmy',                   'Flower farms'),
    ('community_farm',  'Komunitní farmy',                   'Community farms');

-- ─── Locations ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS locations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Bilingual name and description
    name_cs         TEXT NOT NULL,
    name_en         TEXT,
    description_cs  TEXT,
    description_en  TEXT,

    -- Address and GPS
    address         TEXT,
    latitude        REAL,
    longitude       REAL,

    -- Contact
    website         TEXT,
    phone           TEXT,
    email           TEXT,

    -- Opening hours stored as JSON
    -- Example: {"mon": "8:00-12:00", "wed": "8:00-12:00", "sat": "7:00-11:00"}
    -- or free-form: {"note_cs": "Pouze po předchozí domluvě", "note_en": "By appointment only"}
    opening_hours   TEXT,   -- JSON

    -- Social media stored as JSON object with arbitrary keys
    -- Example: {"facebook": "https://...", "instagram": "https://...", "website_alt": "https://..."}
    social_media    TEXT,   -- JSON

    -- Verification
    verified        INTEGER NOT NULL DEFAULT 0,  -- 0 = unverified, 1 = verified

    -- Timestamps
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─── Location–Category junction (many-to-many) ───────────────────────────────

CREATE TABLE IF NOT EXISTS location_categories (
    location_id     INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (location_id, category_id)
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_locations_coords
    ON locations (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_locations_verified
    ON locations (verified);

CREATE INDEX IF NOT EXISTS idx_location_categories_category
    ON location_categories (category_id);
