"""Kör alla kontroller på en gång: ruff, pytest, import av paketet och jämförelse mot baslinjen.

Kör:  .venv/Scripts/python.exe dev/check.py [--rot MAPP] [--spara-baslinje]
I terminalen skrivs en rad per steg (OK/FEL). Hela loggen hamnar i dev/check-logg/ (git-ignorerad).
Pytest körs utan PYTEST_ADDOPTS, med --basetemp under systemets tempmapp (töms först) och utan cache.
Baslinjen: dev/baslinje/kommandon.json listar kommandon (namn, cmd, ev. stdin-fil); varje kommandos utskrift
sparas i dev/baslinje/utdata/<namn>.txt och jämförs vid varje körning. --spara-baslinje skriver om dem.
Före jämförelsen byts mätmappsnamn (data/ÅÅÅÅMMDD-HHMMSS) mot data/MAPP, tempmappens sökväg mot <TMP> och
residualer nära noll mot 0, som i tests/test_facit.py. Kommandona körs med --output i tempmappen så att
inga mätmappar skrivs i repot.
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


def kor(cmd: list[str], cwd: Path, env: dict, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    """Kör ett kommando och fånga utskriften (som byte)."""
    return subprocess.run(cmd, cwd=cwd, env=env, input=stdin, capture_output=True, timeout=300)


def text(b: bytes) -> str:
    """Byte till text, alltid med LF som radslut."""
    return b.decode("utf-8", errors="replace").replace("\r\n", "\n")


def normalisera(s: str, tmp: Path) -> str:
    """Ta bort det som får skilja mellan körningar (samma regler som tests/test_facit.py)."""
    s = s.replace(str(tmp), "<TMP>").replace(tmp.as_posix(), "<TMP>")
    s = re.sub(r"(data[/\x5c]|<TMP>[/\x5c])(\d{8}|ÅÅÅÅMMDD)-(\d{6}|HHMMSS)(-\d+)?", r"\1MAPP", s)
    s = re.sub(r"residual: -?[0-9.]+e-1\d", "residual: 0", s)
    return "\n".join(rad.rstrip() for rad in s.splitlines()).rstrip() + "\n"


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
    ut = text(r.stdout) + text(r.stderr)
    rapport("ruff", r.returncode == 0, (text(r.stdout).strip().splitlines() or ["0 fel"])[-1], ut)

    # 2. pytest (som i CI, men med tempmapp utanför projektet)
    tmp = Path(tempfile.gettempdir()) / "ljuskallor-pytest"
    try:
        if tmp.exists():
            shutil.rmtree(tmp)
    except OSError as e:
        rapport("pytest", False, f"kunde inte tömma {tmp}: {e} (miljöfel, starta om datorn)", str(e))
    else:
        r = kor([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--basetemp", str(tmp)], rot, env)
        ut = text(r.stdout) + text(r.stderr)
        sammanfattning = next((rad for rad in reversed(ut.splitlines()) if re.search(r"\d+ (passed|failed|error)", rad)), "ingen sammanfattning")
        miljofel = re.findall(r"(WinError 5|PermissionError|Access is denied)", ut)
        info = sammanfattning.strip("= ") + (f"  [MILJÖFEL: {len(miljofel)} träffar på WinError 5/PermissionError]" if miljofel else "")
        rapport("pytest", r.returncode == 0, info, ut)

    # 3. import av huvudpaketet
    r = kor([python, "-c", "import spectrometer; print(spectrometer.__file__)"], rot, env)
    ut = text(r.stdout) + text(r.stderr)
    rapport("import", r.returncode == 0, ut.strip().splitlines()[-1] if ut.strip() else "", ut)

    # 4. baslinjens kommandon
    kfil = HAR / "baslinje" / "kommandon.json"
    utmapp = HAR / "baslinje" / "utdata"
    if not kfil.exists():
        rapport("baslinje", True, "ingen baslinje sparad ännu (dev/baslinje/kommandon.json saknas)", "")
    else:
        kommandon = json.loads(kfil.read_text(encoding="utf-8"))
        utmapp.mkdir(exist_ok=True)
        btmp = Path(tempfile.gettempdir()) / "ljuskallor-baslinje"
        shutil.rmtree(btmp, ignore_errors=True)
        btmp.mkdir()
        avvik, loggtext = [], []
        for k in kommandon:
            cmd = [c.replace("{python}", python).replace("{tmp}", str(btmp)) for c in k["cmd"]]
            stdin = (rot / k["stdin"]).read_bytes() if k.get("stdin") else None
            r = kor(cmd, rot / k.get("cwd", "."), env, stdin)
            ut = f"$ {' '.join(k['cmd'])}" + (f" < {k['stdin']}" if k.get("stdin") else "") + f"\n[returkod {r.returncode}]\n"
            ut += normalisera(text(r.stdout) + ("--- stderr ---\n" + text(r.stderr) if r.stderr else ""), btmp)
            fil = utmapp / f"{k['namn']}.txt"
            if a.spara_baslinje:
                fil.write_text(ut, encoding="utf-8", newline="\n")
            elif not fil.exists() or fil.read_text(encoding="utf-8") != ut:
                avvik.append(k["namn"])
                loggtext.append(f"--- {k['namn']}: AVVIKER från {fil.name}\n{ut}")
        if a.spara_baslinje:
            rapport("baslinje", True, f"{len(kommandon)} kommandon sparade till {utmapp.as_posix()}", "")
        else:
            rapport("baslinje", not avvik, f"{len(kommandon) - len(avvik)} av {len(kommandon)} kommandon ger samma utdata" + (f", avviker: {', '.join(avvik)}" if avvik else ""), "\n".join(loggtext))

    logg.write_text("".join(delar), encoding="utf-8", newline="\n")
    print(("ALLT GRÖNT" if fel == 0 else f"{fel} STEG RÖDA") + f"  logg: {logg.as_posix()}")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
