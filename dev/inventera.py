"""Lista varje fil i repot med sökväg, storlek, radantal, sha256, typ och git-status.

Kör:  .venv/Scripts/python.exe dev/inventera.py [--rot MAPP] [--ut FIL.tsv]
Hoppar över .git, .venv, cachar och byggmappar. Utdata är tabbseparerad text (TSV).
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

HOPPA_OVER = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
              "build", "dist", "node_modules", ".pytest-tmp"}
TEXTTYPER = {".py": "python", ".md": "markdown", ".txt": "text", ".toml": "toml", ".yml": "yaml",
             ".yaml": "yaml", ".json": "json", ".csv": "csv", ".ps1": "powershell", ".sh": "shell",
             ".bash": "shell", ".cfg": "config", ".ini": "config", ".html": "html"}
BINARTYPER = {".png": "bild", ".jpg": "bild", ".jpeg": "bild", ".pdf": "pdf", ".npy": "numpy"}


def git_status(rot: Path) -> dict[str, str]:
    """Sökväg -> 'spårad', 'ospårad' eller 'ignorerad'."""
    ut = subprocess.run(["git", "-C", str(rot), "status", "--porcelain", "--ignored", "--untracked-files=all"],
                        capture_output=True, text=True, encoding="utf-8").stdout
    status = {}
    for rad in ut.splitlines():
        kod, sokvag = rad[:2], rad[3:]
        status[sokvag.rstrip("/")] = "ignorerad" if kod == "!!" else "ospårad" if kod == "??" else "ändrad"
    return status


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rot", default=".")
    p.add_argument("--ut", default="-")
    a = p.parse_args()
    rot = Path(a.rot).resolve()
    status = git_status(rot)
    rader = ["sokvag\tbyte\trader\tsha256\ttyp\tgit"]
    for fil in sorted(rot.rglob("*")):
        rel = fil.relative_to(rot)
        if not fil.is_file() or any(d in HOPPA_OVER or d.endswith(".egg-info") for d in rel.parts):
            continue
        data = fil.read_bytes()
        typ = TEXTTYPER.get(fil.suffix.lower()) or BINARTYPER.get(fil.suffix.lower()) or "annat"
        antal = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0) if typ not in BINARTYPER.values() else ""
        relstr = rel.as_posix()
        gs = status.get(relstr)
        if gs is None:  # en ignorerad mapp listas som helhet av git
            gs = next((v for k, v in status.items() if relstr.startswith(k + "/")), "spårad")
        rader.append(f"{relstr}\t{len(data)}\t{antal}\t{hashlib.sha256(data).hexdigest()}\t{typ}\t{gs}")
    text = "\n".join(rader) + "\n"
    if a.ut == "-":
        print(text, end="")
    else:
        Path(a.ut).write_text(text, encoding="utf-8")
        print(f"{len(rader) - 1} filer -> {a.ut}")


if __name__ == "__main__":
    main()
