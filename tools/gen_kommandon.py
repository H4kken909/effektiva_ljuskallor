"""Skriver docs/kommandon.md ur kommandoregistret och fyller tabellen i README.md mellan markörerna.

python tools/gen_kommandon.py          skriver filerna
python tools/gen_kommandon.py --check  skriver inget och ger slutkod 1 om något inte är aktuellt
"""

import inspect
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
START = "<!-- KOMMANDON START -->"
SLUT = "<!-- SLUT -->"


def rows():
    """En rad per kommando i help-ordning: (kommando, syntax, vad, fel), ur registret och docstringarna."""
    sys.path.insert(0, str(ROT))
    from spectrometer import commands, registry

    registry.load(commands.modules())
    result = []
    for cmd in registry.COMMANDS.values():
        paragraphs = (inspect.getdoc(cmd.run) or "").split("\n\n")
        what = paragraphs[0].splitlines()[0] if paragraphs[0] else ""
        errors = " ".join(" ".join(p.split()).removeprefix("Fel: ") for p in paragraphs if p.startswith("Fel:"))
        result.append((cmd.name, cmd.usage or cmd.name, what, errors))
    return result


def table(rows_, headings, columns):
    """En Markdown-tabell med de givna kolumnerna (index i varje rad); | i texten skrivs \\|, tom cell blir –."""
    lines = ["| " + " | ".join(headings) + " |", "|" + "---|" * len(headings)]
    for row in rows_:
        cells = [row[i].replace("|", "\\|") or "–" for i in columns]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def document(rows_):
    """Hela docs/kommandon.md."""
    intro = "Skapad av `python tools/gen_kommandon.py` ur kommandoregistret. Ändra texterna i koden, inte här."
    return "# Kommandon\n\n" + intro + "\n\n" + table(rows_, ("kommando", "syntax", "vad", "fel"), (0, 1, 2, 3)) + "\n"


def fill(text, block):
    """text med raderna mellan START och SLUT utbytta mot block; None om markörerna saknas."""
    start = text.find(START)
    end = text.find(SLUT)
    if start == -1 or end < start:
        return None
    return text[: start + len(START)] + "\n" + block + "\n" + text[end:]


def wanted(rows_):
    """Filerna som ska finnas och deras text: docs/kommandon.md alltid, README.md bara om den har markörerna."""
    result = {ROT / "docs" / "kommandon.md": document(rows_)}
    readme = ROT / "README.md"
    if readme.exists():
        filled = fill(readme.read_text(encoding="utf-8"), table(rows_, ("kommando", "syntax", "vad"), (0, 1, 2)))
        if filled is not None:
            result[readme] = filled
    return result


def main(args):
    """Skriver de filer som inte är aktuella, eller med --check bara säger vilka. Ger slutkoden."""
    stale = []
    for path, text in wanted(rows()).items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append((path, text))
    if "--check" in args:
        for path, _ in stale:
            print(f"{path.relative_to(ROT).as_posix()} är inte aktuell. Kör python tools/gen_kommandon.py")
        return 1 if stale else 0
    for path, text in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Skrev {path.relative_to(ROT).as_posix()}")
    if not stale:
        print("Allt är redan aktuellt.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
