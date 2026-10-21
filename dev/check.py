"""Kör alla kontroller på en gång: ruff, pytest, import av paketet och jämförelse mot baslinjen.

Kör:  .venv/Scripts/python.exe dev/check.py [--rot MAPP] [--spara-baslinje]
I terminalen skrivs en rad per steg (OK/FEL). Hela loggen hamnar i dev/check-logg/ (git-ignorerad).
Pytest körs utan PYTEST_ADDOPTS, med --basetemp under systemets tempmapp (töms först) och utan cache.
Baslinjen: dev/baslinje/kommandon.json listar kommandon; varje kommandos utskrift sparas i
dev/baslinje/utdata/<namn>.txt och jämförs vid varje körning. --spara-baslinje skriver om dem.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HAR = Path(__file__).resolve().parent  # dev/


def kor(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Kör ett kommando och fånga utskriften."""
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")


def main() -> int:
    """Kör alla steg; returnerar 0 om allt är grönt."""
    p = argparse.ArgumentParser()
    p.add_argument("--rot", default=str(HAR.parent), help="repot som ska kontrolleras (standard: det här repot)")
    p.add_argument("--spara-baslinje", action="store_true", help="skriv om dev/baslinje/utdata/ i stället för att jämföra")
    a = p.parse_args()
    rot = Path(a.rot).resolve()
    python = sys.executable
    loggmapp = HAR / "check-logg"
    loggmapp.mkdir(exist_ok=True)
    logg = loggmapp / time.strftime("check-%Y%m%d-%H%M%S.log")
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("MPLBACKEND", "Agg")
    fel = 0
    delar: list[str] = [f"rot={rot}\npython={python}\n"]

    def rapport(namn: str, ok: bool, info: str, utskrift: str) -> None:
        nonlocal fel
        fel += 0 if ok else 1
        delar.append(f"\n{'=' * 20} {namn}: {'OK' if ok else 'FEL'} {info}\n{utskrift}")
        print(f"{'OK ' if ok else 'FEL'} {namn}: {info}  ({logg.as_posix()})")

    # 1. ruff (som i CI)
    r = kor([python, "-m", "ruff", "check", "."], rot, env)
    rapport("ruff", r.returncode == 0, (r.stdout.strip().splitlines() or ["0 fel"])[-1], r.stdout + r.stderr)

    # 2. pytest (som i CI, men med tempmapp utanför projektet)
    tmp = Path(tempfile.gettempdir()) / "ljuskallor-pytest"
    try:
        shutil.rmtree(tmp, ignore_errors=False) if tmp.exists() else None
    except OSError as e:
        rapport("pytest", False, f"kunde inte tömma {tmp}: {e} (miljöfel, starta om datorn)", str(e))
        r = None
    else:
        r = kor([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(tmp)], rot, env)
    if r is not None:
        sammanfattning = next((rad for rad in reversed(r.stdout.splitlines()) if re.search(r"\d+ (passed|failed|error)", rad)), "ingen sammanfattning")
        miljofel = re.findall(r"(WinError 5|PermissionError|Access is denied)", r.stdout + r.stderr)
        info = sammanfattning.strip("= ") + (f"  [MILJÖFEL: {len(miljofel)} träffar på WinError 5/PermissionError]" if miljofel else "")
        rapport("pytest", r.returncode == 0, info, r.stdout + r.stderr)

    # 3. import av huvudpaketet
    r = kor([python, "-c", "import spectrometer; print(spectrometer.__file__)"], rot, env)
    rapport("import", r.returncode == 0, r.stdout.strip() or r.stderr.strip().splitlines()[-1:][0] if (r.stdout or r.stderr) else "", r.stdout + r.stderr)

    # 4. baslinjens kommandon
    kfil = HAR / "baslinje" / "kommandon.json"
    utmapp = HAR / "baslinje" / "utdata"
    if not kfil.exists():
        rapport("baslinje", True, "ingen baslinje sparad ännu (dev/baslinje/kommandon.json saknas)", "")
    else:
        kommandon = json.loads(kfil.read_text(encoding="utf-8"))
        utmapp.mkdir(exist_ok=True)
        avvik, text = [], []
        for k in kommandon:
            cmd = [python if c == "{python}" else c for c in k["cmd"]]
            r = kor(cmd, rot / k.get("cwd", "."), env)
            ut = f"$ {' '.join(k['cmd'])}\n[returkod {r.returncode}]\n{r.stdout}{r.stderr}"
            fil = utmapp / f"{k['namn']}.txt"
            if a.spara_baslinje:
                fil.write_text(ut, encoding="utf-8", newline="\n")
            elif not fil.exists() or fil.read_text(encoding="utf-8") != ut:
                avvik.append(k["namn"])
                text.append(f"--- {k['namn']}: AVVIKER från {fil.name}\n{ut}")
        if a.spara_baslinje:
            rapport("baslinje", True, f"{len(kommandon)} kommandon sparade till {utmapp.as_posix()}", "")
        else:
            rapport("baslinje", not avvik, f"{len(kommandon) - len(avvik)} av {len(kommandon)} kommandon ger samma utdata" + (f", avviker: {', '.join(avvik)}" if avvik else ""), "\n".join(text))

    logg.write_text("".join(delar), encoding="utf-8", newline="\n")
    print(("ALLT GRÖNT" if fel == 0 else f"{fel} STEG RÖDA") + f"  logg: {logg.as_posix()}")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
