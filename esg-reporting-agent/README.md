# ESG Reporting of Small Businesses

Projekt pro kvalitativní analýzu rozhovorů s mikropodnikateli pomocí dvou AI agentů.

---

## Přehled

| Agent | Soubor | Vstup | Výstup |
|---|---|---|---|
| Agent 1 — Kódování | `agent1_coding.py` | `.docx` nebo `.txt` rozhovor | `coded_interviews/<název>_coded.txt` |
| Agent 2 — Analýza | `agent2_analysis.py` | Všechny soubory v `coded_interviews/` | `output/analysis_report.txt` |

---

## Instalace

**1. Naklonuj repozitář a přejdi do složky:**
```bash
cd "ESG Reporting of Small Businesses"
```

**2. Vytvoř a aktivuj virtuální prostředí (doporučeno):**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

**3. Nainstaluj závislosti:**
```bash
pip install -r requirements.txt
```

**4. Nastav API klíč:**
```bash
cp .env.example .env
```
Otevři `.env` a doplň svůj Anthropic API klíč:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Struktura projektu

```
.
├── agent1_coding.py        # Agent 1: kódování jednotlivých rozhovorů
├── agent2_analysis.py      # Agent 2: analýza všech zakódovaných rozhovorů
├── requirements.txt
├── .env.example
├── .gitignore
├── raw_interviews/         # Sem vkládej surové přepisy (.docx / .txt) — NENÍ v gitu
├── coded_interviews/       # Agent 1 sem ukládá zakódované výstupy
└── output/
    └── analysis_report.txt # Agent 2 sem ukládá finální zprávu
```

---

## Použití

### Agent 1 — Kódování rozhovoru

Spusť pro každý rozhovor zvlášť:

```bash
python agent1_coding.py raw_interviews/rozhovor_01.docx
python agent1_coding.py raw_interviews/rozhovor_02.txt
```

Výstup se uloží do `coded_interviews/rozhovor_01_coded.txt` atd.

**Podporované formáty:** `.docx` (Word) a `.txt` (prostý text, kódování UTF-8)

---

### Agent 2 — Analytická zpráva

Po zakódování všech rozhovorů spusť:

```bash
python agent2_analysis.py
```

Agent automaticky načte všechny soubory ze složky `coded_interviews/` a vygeneruje kompletní zprávu do `output/analysis_report.txt`.

---

## Kodovací schéma (Agent 1)

| # | Oblast | Kódy |
|---|---|---|
| 1 | Charakteristika podniku | FIRMA_VELIKOST, FIRMA_OBOR, FIRMA_HISTORIE |
| 2 | Nákupní strategie | STRATEGIE_FORMALNI, STRATEGIE_NEFORMALNI, STRATEGIE_VYVOJ |
| 3 | Výběr dodavatelů | DODAVATEL_POCET, DODAVATEL_VYBER, DODAVATEL_KRITERIA, DODAVATEL_VZTAHY |
| 4 | Nákupní proces | PROCES_ROZHODOVANI, PROCES_OBJEDNAVANI, PROCES_CAS, PROCES_DOKUMENTACE |
| 5 | Vyjednávání | VYJEDNAVANI_STRATEGIE, VYJEDNAVANI_SLEVY, VYJEDNAVANI_PLATBY |
| 6 | Problémy a rizika | PROBLEM_DODAVATEL, PROBLEM_FINANCE, PROBLEM_RESENI, RIZIKO_MANAGEMENT |
| 7 | Digitalizace | TECH_SOUCASNE, TECH_BARIERY, TECH_POTREBY |
| 8 | Umělá inteligence | AI_VYUZITI, AI_POTENCIAL, AI_OBAVY |
| 9 | Ekonomické aspekty | EKONOMIKA_NAKLADY, EKONOMIKA_EFEKTIVITA |
| 10 | Specifika mikropodniku | MIKRO_VYHODY, MIKRO_NEVYHODY, MIKRO_SPECIFIKA |

---

## Co generuje Agent 2

- Frekvenční analýza kódů (tabulka + TOP 10)
- Tematická analýza (dominantní / minoritní / unikátní témata)
- Srovnání firemního vs. soukromého nákupu
- Vzorce a souvislosti mezi proměnnými
- Typologie mikropodnikatelů (Typ A / B / C)
- TOP 5 problémů a TOP 5 potřeb
- Specifika mikropodniků vs. velké firmy
- Role technologií a AI
- Hlavní zjištění (5–7 bodů)
- Závěrečná syntéza s doporučeními

---

## Poznámky

- Surové přepisy v `raw_interviews/` jsou vyloučeny z gitu (`.gitignore`) kvůli ochraně dat respondentů.
- Soubory `.env` s API klíčem jsou také vyloučeny z gitu.
- Model: `claude-opus-4-6` s streamingem pro dlouhé výstupy.
