# FarMappa

**A bilingual Czech/English database and map of organic and local food producers in the Czech Republic.**

---

## English

FarMappa is an open database of organic farms, local food producers, and farmers' markets across the Czech Republic. The goal is to make it easy for people to find verified sources of local, organic, and sustainably produced food near them.

### Features
- Bilingual (Czech/English) names and descriptions for every location
- GPS coordinates for map integration
- Support for multiple categories per location (e.g. a farm can be tagged as both eggs and vegetables)
- Verified/unverified status flag
- Opening hours, contact info, and flexible social media links

### Categories
| English | Czech |
|---|---|
| Farmers' market | Farmářský trh |
| Beekeeper | Včelař |
| Organic goat milk and products | Bio kozí mléko a produkty |
| Organic meat | Bio maso |
| Potatoes | Brambory |
| Vegetables | Zelenina |
| Fruits | Ovoce |
| Self-picking (Samosběr) | Samosběr |
| Organic grains | Bio obiloviny |
| Dairy and dairy products | Mléčné výrobky (bio/pastevní/travní) |
| Organic eggs | Bio vejce |
| Sheep's milk and products | Ovčí mléko a produkty |

### Project Structure
```
FarMappa/
├── agents/        # AI agents for data collection, verification, and enrichment
├── database/      # SQLite database file and schema
├── scripts/       # Utility scripts (create DB, import data, export, etc.)
└── README.md
```

### Setup
```bash
python scripts/create_db.py
```

---

## Česky

FarMappa je otevřená databáze ekologických farem, místních výrobců potravin a farmářských trhů po celé České republice. Cílem je usnadnit lidem hledání ověřených zdrojů lokálních, bio a udržitelně vypěstovaných potravin v jejich okolí.

### Funkce
- Dvojjazyčné (česky/anglicky) názvy a popisy každé lokality
- GPS souřadnice pro integraci s mapou
- Podpora více kategorií pro jednu lokalitu (např. farma může být zároveň v kategoriích vejce i zelenina)
- Příznak ověřeno/neověřeno
- Otevírací doba, kontaktní údaje a flexibilní pole pro sociální sítě

### Kategorie
| Česky | English |
|---|---|
| Farmářský trh | Farmers' market |
| Včelař | Beekeeper |
| Bio kozí mléko a produkty | Organic goat milk and products |
| Bio maso | Organic meat |
| Brambory | Potatoes |
| Zelenina | Vegetables |
| Ovoce | Fruits |
| Samosběr | Self-picking |
| Bio obiloviny | Organic grains |
| Mléčné výrobky (bio/pastevní/travní) | Dairy and dairy products |
| Bio vejce | Organic eggs |
| Ovčí mléko a produkty | Sheep's milk and products |

### Struktura projektu
```
FarMappa/
├── agents/        # AI agenti pro sběr dat, ověřování a obohacování
├── database/      # Soubor SQLite databáze a schéma
├── scripts/       # Pomocné skripty (vytvoření DB, import dat, export atd.)
└── README.md
```

### Spuštění
```bash
python scripts/create_db.py
```
