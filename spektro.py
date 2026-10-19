"""Starta spektrometern: py -m spektro (Windows) eller python3 -m spektro (Linux).

Körs i projektmappen. Första gången byggs .venv här och requirements.txt
installeras; när requirements.txt ändras installeras den igen. Sedan körs
programmet alltid i den miljön, utan att någon aktiverar den.

Utan flaggor: maximerat fönster, gul text medan modulerna laddas, färgprismat
ur startskarm/prisma.py och sedan prompten. --windowed lämnar fönstret som
det är, --no-splash går direkt till prompten, --delay ändrar pausen mellan
raderna. Övriga flaggor skickas till spectrometer.main. Utan terminal
(omdirigerad in- eller utmatning, som i jamfor och pytest) startas
spectrometer.main direkt med oförändrad utskrift.
"""

import argparse
import builtins
import hashlib
import importlib
import importlib.util
import io
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROT = Path(__file__).resolve().parent
VENV = ROT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
KRAV = ROT / "requirements.txt"
MARKOR = VENV / ".spektro-krav"

# Startskärmen: ändra här.
TEXT = ["Inget prat", "Inget spring", "Inget fniss", "Inget alls!"]
PAUS_START = 0.4  # sekunder med svart skärm innan första raden
PAUS_RAD = 0.0  # sekunder mellan raderna (kan ändras per körning med --delay)
PAUS_SLUT = 1  # sekunder efter sista gula raden innan teamet visas

# Färgerna på startskärmen (ANSI-koder; vt_windows slår på dem i Windows-konsolen).
GUL = "\x1b[1;33m"  # fet gul: de fyra raderna
FET = "\x1b[1m"  # fet: projektraden
VIT = "\x1b[1;97m"  # fet vit: Elias och Adrian
GRA = "\x1b[38;5;247m"  # grå: versionen, övriga i teamet och help-tipset
NOLL = "\x1b[0m"  # tillbaka till terminalens färger

VERSION = "v1.0.0"
PROJEKT = "Grupp GRYb1  ·  Effektiva ljuskällor  ·  TFYY51 Ingenjörsprojekt, HT 2026"
TEAM = [
    ("Elias Holmberg", "Programmeringsansvarig", True),
    ("Adrian Lindstedt", "Labb, test och kvalitet", True),
    ("Alan Hosseini", "Projektledare", False),
    ("Isak Jansson", "Dokumentansvarig", False),
    ("Oscar Al-Ishak", "Design och optik", False),
]

MODULER = [
    "numpy",
    "cv2",
    "matplotlib.pyplot",
    "spectrometer.calc",
    "spectrometer.files",
    "spectrometer.source",
    "spectrometer.plot",
]


def skriv(text):
    """Skriv text direkt till terminalen."""
    sys.stdout.write(text)
    sys.stdout.flush()


def skriv_rad(text="", farg=""):
    """Skriv en rad i färgen farg (koderna ovan) och återställ färgen efter."""
    skriv(f"{farg}{text}{NOLL}\n" if farg else f"{text}\n")


def finns(namn):
    """Sant om modulen namn går att importera."""
    try:
        return importlib.util.find_spec(namn) is not None
    except ModuleNotFoundError:
        return False


def las_flaggor():
    """Läs spektros egna flaggor; övriga lämnas till spectrometer.main."""
    tolk = argparse.ArgumentParser(
        prog="spektro",
        description="Startar spektrometern med startskärm i maximerat fönster.",
        epilog="Andra flaggor skickas vidare till spectrometer.main.",
        allow_abbrev=False,
    )
    tolk.add_argument("--windowed", action="store_true", help="maximera inte fönstret")
    tolk.add_argument(
        "--no-splash", action="store_true", help="ingen startskärm, direkt till prompten"
    )
    tolk.add_argument(
        "--delay",
        type=float,
        default=PAUS_RAD,
        metavar="SEK",
        help=f"paus mellan raderna i sekunder (standard {PAUS_RAD})",
    )
    return tolk.parse_known_args()


def ordna_miljon():
    """Bygg .venv om den saknas och installera requirements.txt när den ändrats."""
    try:
        if not VENV_PY.exists():
            print("Första gången: bygger miljön i .venv ...")
            subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        summa = hashlib.sha256(KRAV.read_bytes()).hexdigest()
        if not MARKOR.exists() or MARKOR.read_text() != summa:
            print("Installerar paketen i requirements.txt ...")
            pip = [str(VENV_PY), "-m", "pip", "install", "-q", "-r", str(KRAV)]
            subprocess.run(pip, check=True)
            MARKOR.write_text(summa)
    except (OSError, subprocess.CalledProcessError) as fel:
        sys.exit(f"Kunde inte ordna miljön i {VENV}: {fel}")


def kor_i_miljon():
    """Kör spektro.py igen med Python i .venv och avsluta med dess kod."""
    barn = subprocess.Popen([str(VENV_PY), str(ROT / "spektro.py"), *sys.argv[1:]])
    while True:
        try:
            sys.exit(barn.wait())
        except KeyboardInterrupt:
            continue  # Ctrl+C hanteras av programmet, inte av startaren


def vt_windows():
    """Slå på färg- och skärmkoder i Windows-konsolen."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    ut = k32.GetStdHandle(-11)
    lage = wintypes.DWORD()
    if k32.GetConsoleMode(ut, ctypes.byref(lage)):
        k32.SetConsoleMode(ut, lage.value | 0x0004)


def maximera_windows():
    """Maximera terminalfönstret (titelrad och knappar kvar), om det är vårt."""
    import ctypes
    from ctypes import wintypes

    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GetConsoleWindow.restype = wintypes.HWND
    u32.GetForegroundWindow.restype = wintypes.HWND
    for f in (u32.GetWindow, u32.GetAncestor):
        f.restype = wintypes.HWND
        f.argtypes = [wintypes.HWND, wintypes.UINT]
    u32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    konsol = k32.GetConsoleWindow()
    fram = u32.GetForegroundWindow()
    if not konsol or not fram:
        return
    if fram not in (konsol, u32.GetWindow(konsol, 4), u32.GetAncestor(konsol, 3)):
        return  # fönstret i fokus är inte vårt: rör det inte
    u32.ShowWindow(fram, 3)  # 3 = SW_MAXIMIZE
    time.sleep(0.2)


def maximera_linux():
    """Maximera terminalfönstret med wmctrl eller xterm-koden."""
    if shutil.which("wmctrl"):
        lage = "add,maximized_vert,maximized_horz"
        subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", lage], check=False)
    else:
        skriv("\x1b[9;1t")  # xterm-koden för maximera
    time.sleep(0.2)


def rensa():
    """Töm skärmen och rullningshistoriken."""
    skriv("\x1b[2J\x1b[3J\x1b[H")


def rita_prisma():
    """Rita färgprismat centrerat, med plats för prompten under."""
    if not finns("startskarm.prisma"):
        return
    from startskarm import prisma

    kolumner, rader = shutil.get_terminal_size((120, 40))
    bredd = max(20, min(kolumner - 2, max(4, rader - 22) * 4))
    hojd = max(5, round(bredd / 4))  # teckenceller ungefär dubbelt så höga
    vanster = " " * max(0, (kolumner - bredd) // 2)
    linjer = prisma.render("color", bredd, hojd)
    skriv("\n" + "\n".join(vanster + linje for linje in linjer) + "\n\n")


def gom_hjalpen():
    """Svälj det main skriver före första prompten (hjälpen); prismat står där."""
    ekta_input, ekta_ut = builtins.input, sys.stdout
    sys.stdout = io.StringIO()

    def forsta_input(prompt=""):
        sys.stdout = ekta_ut
        builtins.input = ekta_input
        return ekta_input(prompt)

    builtins.input = forsta_input


def kor_main():
    """Kör spectrometer.main som om den startats med python -m."""
    runpy.run_module("spectrometer.main", run_name="__main__", alter_sys=True)


def skriv_info():
    """Projekt, version, teamet (Elias och Adrian framhävda) och help-tipset."""
    skriv_rad()
    skriv_rad(f"  {PROJEKT}", FET)
    skriv_rad(f"  Spektro {VERSION}", GRA)
    skriv_rad()
    for namn, ansvar, framhav in TEAM:
        stil = VIT if framhav else GRA
        skriv_rad(f"    {namn:<18} {ansvar}", stil)
    skriv_rad()
    skriv_rad('  Skriv "help" för kommandona, "quit" för att avsluta.', GRA)
    skriv_rad()


def startskarm(paus_rad):
    """Svart skärm, prismat, gul text medan modulerna laddas, teamet, sedan main."""
    try:
        skriv("\x1b[0;37;40m\x1b[?25l")  # svart bakgrund, ingen markör
        rensa()
        time.sleep(PAUS_START)
        rita_prisma()
        for rad in TEXT:
            skriv_rad(f"  {rad}", GUL)
            time.sleep(paus_rad)
        for namn in MODULER:
            if finns(namn):
                importlib.import_module(namn)
        time.sleep(PAUS_SLUT)
        skriv_info()
        skriv("\x1b[?25h")
        main_py = ROT / "spectrometer" / "main.py"
        if "input(" in main_py.read_text(encoding="utf-8"):
            gom_hjalpen()
        kor_main()
    finally:
        if isinstance(sys.stdout, io.StringIO):
            # main slutade före första prompten: visa det den skrev ändå
            kvar = sys.stdout.getvalue()
            sys.stdout = sys.__stdout__
            skriv(kvar)
        skriv("\x1b[?25h\x1b[0m")


def main():
    """Läs flaggorna, ordna miljön och starta programmet."""
    args, resten = las_flaggor()
    ordna_miljon()
    if Path(sys.prefix).resolve() != VENV.resolve():
        kor_i_miljon()
    sys.argv = [sys.argv[0], *resten]
    if args.no_splash or not (sys.stdin.isatty() and sys.stdout.isatty()):
        kor_main()
        return
    if sys.platform == "win32":
        vt_windows()
    if not args.windowed:
        if sys.platform == "win32":
            maximera_windows()
        else:
            maximera_linux()
    startskarm(max(0.0, args.delay))


if __name__ == "__main__":
    main()