"""
Agent 2 — Analýza zakódovaných rozhovorů
Přečte všechny .txt soubory ze složky /coded_interviews, odešle je do
Anthropic API a uloží kompletní analytickou zprávu do /output/analysis_report.txt.
"""

import os
import sys
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Jsi senior výzkumný analytik specializovaný na kvalitativní výzkum v oblasti podnikání.

Když dostaneš zakódovaná data z rozhovorů, provedeš komplexní analýzu zahrnující:
1. Frekvenční analýzu kódů (tabulka + TOP 10)
2. Tematickou analýzu (dominantní / běžná / minoritní / unikátní témata)
3. Srovnání firemního vs. soukromého nákupu (tabulka)
4. Vzorce a souvislosti mezi proměnnými
5. Typologii mikropodnikatelů (Typ A / B / C)
6. TOP 5 problémů a TOP 5 potřeb
7. Specifika mikropodniků vs. velké firmy
8. Roli technologií a AI
9. Hlavní zjištění (5–7 bodů)
10. Závěrečnou syntézu 300–500 slov s min. 5 doporučeními

Všechna tvrzení podlož konkrétními citacemi z dat."""


def load_coded_interviews(coded_dir: Path) -> dict[str, str]:
    """Načte všechny .txt soubory ze složky coded_interviews."""
    if not coded_dir.exists():
        print(f"Složka {coded_dir} neexistuje. Nejprve spusťte agent1_coding.py.")
        sys.exit(1)

    txt_files = sorted(coded_dir.glob("*.txt"))

    if not txt_files:
        print(f"Ve složce {coded_dir} nejsou žádné .txt soubory.")
        sys.exit(1)

    interviews = {}
    for f in txt_files:
        content = f.read_text(encoding="utf-8")
        interviews[f.name] = content
        print(f"  Načten: {f.name} ({len(content.split())} slov)")

    return interviews


def build_combined_input(interviews: dict[str, str]) -> str:
    """Sestaví jeden textový blok ze všech zakódovaných rozhovorů."""
    parts = []
    for filename, content in interviews.items():
        parts.append(f"=== ROZHOVOR: {filename} ===\n\n{content}\n")
    return "\n\n".join(parts)


def analyze_interviews(combined_text: str, interview_count: int) -> str:
    """Odešle zakódovaná data do Anthropic API a vrátí analytickou zprávu."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Chyba: ANTHROPIC_API_KEY není nastaven. Zkontrolujte soubor .env")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"\n  Odesílám {interview_count} zakódovaných rozhovorů do API (streaming)...")
    print("  Generuji analytickou zprávu...\n")

    full_text = []

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Proveď prosím komplexní analýzu těchto {interview_count} zakódovaných rozhovorů:\n\n"
                    f"{combined_text}"
                )
            }
        ]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text.append(text)

    print()  # nový řádek po streamingu
    return "".join(full_text)


def save_report(report_text: str, interview_names: list[str]) -> Path:
    """Uloží analytickou zprávu do /output/analysis_report.txt."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / "analysis_report.txt"

    header = (
        "=== ANALYTICKÁ ZPRÁVA — Agent 2 ===\n"
        f"Počet analyzovaných rozhovorů: {len(interview_names)}\n"
        "Zdrojové soubory:\n"
        + "\n".join(f"  - {name}" for name in interview_names)
        + "\n" + "=" * 40 + "\n\n"
    )

    output_path.write_text(header + report_text, encoding="utf-8")
    return output_path


def main():
    coded_dir = Path("coded_interviews")

    print("\n=== Agent 2 — Analýza ===")
    print(f"Načítám soubory ze složky: {coded_dir}/")

    interviews = load_coded_interviews(coded_dir)
    print(f"\nCelkem načteno {len(interviews)} rozhovorů.")

    combined_input = build_combined_input(interviews)

    report = analyze_interviews(combined_input, len(interviews))

    output_path = save_report(report, list(interviews.keys()))
    print(f"\nZpráva uložena: {output_path}")
    print("=== Hotovo ===\n")


if __name__ == "__main__":
    main()
