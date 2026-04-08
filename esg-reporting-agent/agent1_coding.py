"""
Agent 1 — Kódování rozhovorů
Přečte .docx nebo .txt přepis rozhovoru, zakóduje ho pomocí Anthropic API
a uloží výstup do složky /coded_interviews.
"""

import os
import sys
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Jsi výzkumný asistent specializovaný na kvalitativní analýzu dat. Vždy pracuješ jako Agent 1 — Kódování.

Když dostaneš přepis rozhovoru, automaticky ho zakóduješ podle tohoto schématu:

KODOVACÍ SCHÉMA:
1. CHARAKTERISTIKA PODNIKU: FIRMA_VELIKOST / FIRMA_OBOR / FIRMA_HISTORIE
2. NÁKUPNÍ STRATEGIE: STRATEGIE_FORMALNI / STRATEGIE_NEFORMALNI / STRATEGIE_VYVOJ
3. VÝBĚR DODAVATELŮ: DODAVATEL_POCET / DODAVATEL_VYBER / DODAVATEL_KRITERIA / DODAVATEL_VZTAHY
4. NÁKUPNÍ PROCES: PROCES_ROZHODOVANI / PROCES_OBJEDNAVANI / PROCES_CAS / PROCES_DOKUMENTACE
5. VYJEDNÁVÁNÍ: VYJEDNAVANI_STRATEGIE / VYJEDNAVANI_SLEVY / VYJEDNAVANI_PLATBY
6. PROBLÉMY A RIZIKA: PROBLEM_DODAVATEL / PROBLEM_FINANCE / PROBLEM_RESENI / RIZIKO_MANAGEMENT
7. DIGITALIZACE: TECH_SOUCASNE / TECH_BARIERY / TECH_POTREBY
8. UMĚLÁ INTELIGENCE: AI_VYUZITI / AI_POTENCIAL / AI_OBAVY
9. EKONOMICKÉ ASPEKTY: EKONOMIKA_NAKLADY / EKONOMIKA_EFEKTIVITA
10. SPECIFIKA MIKROPODNIKU: MIKRO_VYHODY / MIKRO_NEVYHODY / MIKRO_SPECIFIKA

FORMÁT VÝSTUPU — pro každý úsek:
KÓD: [název]
CITACE: "[přesná citace]"
OTÁZKA: [kde v rozhovoru]
POZNÁMKA: [proč přiřazen]
---

Na konci vždy přidej ZÁVĚREČNOU ANALÝZU:
- Celkový počet kódů
- TOP 5 nejčastějších kódů
- Chybějící kódy
- 3–5 hlavních témat
- Doporučení pro další otázky"""


def read_interview(file_path: Path) -> str:
    """Přečte rozhovor ze souboru .docx nebo .txt."""
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    elif suffix == ".docx":
        try:
            from docx import Document
        except ImportError:
            print("Chyba: python-docx není nainstalován. Spusťte: pip install python-docx")
            sys.exit(1)
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    else:
        print(f"Nepodporovaný formát souboru: {suffix}. Podporovány jsou .docx a .txt")
        sys.exit(1)


def code_interview(transcript: str, filename: str) -> str:
    """Odešle přepis do Anthropic API a vrátí zakódovaný výstup."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Chyba: ANTHROPIC_API_KEY není nastaven. Zkontrolujte soubor .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"  Odesílám rozhovor do API (streaming)...")

    full_text = []

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Zakóduj prosím tento rozhovor:\n\n{transcript}"
            }
        ]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text.append(text)

    print()  # nový řádek po streamingu
    return "".join(full_text)


def save_coded_output(coded_text: str, source_filename: str) -> Path:
    """Uloží zakódovaný výstup do složky /coded_interviews."""
    output_dir = Path("coded_interviews")
    output_dir.mkdir(exist_ok=True)

    stem = Path(source_filename).stem
    output_path = output_dir / f"{stem}_coded.txt"

    output_path.write_text(coded_text, encoding="utf-8")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Použití: python agent1_coding.py <cesta_k_souboru>")
        print("Příklad: python agent1_coding.py raw_interviews/rozhovor_01.docx")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Soubor nenalezen: {file_path}")
        sys.exit(1)

    print(f"\n=== Agent 1 — Kódování ===")
    print(f"Soubor: {file_path}")
    print(f"Čtu rozhovor...")

    transcript = read_interview(file_path)
    word_count = len(transcript.split())
    print(f"Načteno {word_count} slov.\n")

    print("Kóduji rozhovor...\n")
    coded_output = code_interview(transcript, file_path.name)

    output_path = save_coded_output(coded_output, file_path.name)
    print(f"\nVýstup uložen: {output_path}")
    print("=== Hotovo ===\n")


if __name__ == "__main__":
    main()
