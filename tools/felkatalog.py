"""Felkatalog, steg 1: varje raise med en text i spectrometer/ som en tabell i docs/felkatalog.md.

Kör från repots rot: python tools/felkatalog.py (eller med en annan målfil: python tools/felkatalog.py UT.md).
Felkoden är det som står före första kolon, t.ex. input.invalid_argument; {namn} fylls i när felet händer.
"""

import ast
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]


def text_of(node):
    """Texten i ett strängargument; i en f-sträng står uttrycken kvar som {namn}. None om det inte är en sträng."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                parts.append(part.value)
            else:
                conversion = f"!{chr(part.conversion)}" if part.conversion > 0 else ""
                spec = f":{text_of(part.format_spec)}" if part.format_spec is not None else ""
                parts.append("{" + ast.unparse(part.value) + conversion + spec + "}")
        return "".join(parts)
    return None


def split_code(text):
    """Delar "input.missing_data: Ingen mätning än." i felkod och text; utan felkod blir koden tom."""
    code, _sep, rest = text.partition(": ")
    if "." in code and " " not in code:
        return code, rest
    return "", text


def raises(path):
    """Varje raise X("...") i filen, i filordning, som (funktion, undantag, felkod, text).

    raise X(message) räknas också när message = "..." står tidigare i samma funktion (som i source.open_source);
    får variabeln olika texter i flera grenar ger raisen en rad per text.
    """
    found = []
    named = {}  # (funktion, variabel): alla texter variabeln får i funktionen, i ordning

    def visit(node, func):
        """Går igenom noden; func är namnet på den närmaste funktionen runt den."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef):
                visit(child, child.name)
                continue
            if isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                text = text_of(child.value)
                if text is not None:
                    texts = named.setdefault((func, child.targets[0].id), [])
                    if text not in texts:
                        texts.append(text)
            if isinstance(child, ast.Raise) and isinstance(child.exc, ast.Call) and child.exc.args:
                arg = child.exc.args[0]
                if isinstance(arg, ast.Name):
                    texts = named.get((func, arg.id), [])
                else:
                    direct = text_of(arg)
                    texts = [] if direct is None else [direct]
                for text in texts:
                    found.append((func, ast.unparse(child.exc.func), *split_code(text)))
            visit(child, func)

    visit(ast.parse(path.read_text(encoding="utf-8")), "")
    return found


def main():
    """Skriver katalogen till docs/felkatalog.md, eller till filen i första argumentet. Ger slutkoden 0."""
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROT / "docs" / "felkatalog.md"
    rows = []
    for path in sorted((ROT / "spectrometer").rglob("*.py")):
        for func, exc, code, text in raises(path):
            text = text.replace("|", "\\|")  # | delar kolumnerna i en Markdown-tabell
            rows.append(f"| {path.relative_to(ROT).as_posix()} | {func} | {exc} | {code} | {text} |")
    lines = [
        "# Felkatalog",
        "",
        "Skapad av `python tools/felkatalog.py` ur koden. Ändra inte för hand: kör skriptet igen efter en ändring.",
        "På skärmen står felet som `Fel: felkod: text`; `{namn}` fylls i när felet händer.",
        "",
        "| fil | funktion | undantag | felkod | text |",
        "|---|---|---|---|---|",
        *rows,
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shown = target.relative_to(ROT).as_posix() if target.is_relative_to(ROT) else target.as_posix()
    print(f"skrev {shown}: {len(rows)} felrader")
    return 0


if __name__ == "__main__":
    sys.exit(main())
