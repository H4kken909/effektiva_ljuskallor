"""Starta spektrometern: py -m spektro (Windows) eller python3 -m spektro (Linux).

Körs i projektmappen. Första gången byggs .venv här och requirements.txt installeras; när requirements.txt ändras
installeras den igen. Sedan körs programmet alltid i den miljön, utan att någon aktiverar den.

Paketen installeras bara som färdiga paket (wheels), aldrig genom att kompilera. Saknar Pythonen som startade
spektro färdiga paket (32-bitars, ARM, free-threaded eller för ny version) letar startaren upp en annan installerad
Python som har dem och bygger .venv med den; finns ingen säger den vad som ska installeras.

Utan flaggor: maximerat fönster, gul text medan modulerna laddas, färgprismat ur startskarm/prisma.py och sedan
prompten. --windowed lämnar fönstret som det är, --no-splash går direkt till prompten, --delay ändrar pausen mellan
raderna. Övriga flaggor skickas till spectrometer.main. Utan terminal (omdirigerad in- eller utmatning, som i jamfor
och pytest) startas spectrometer.main direkt med oförändrad utskrift.
"""

import argparse
import builtins
import hashlib
import importlib
import io
import re
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path

from spectrometer import __version__

VERSION = f"v{__version__}"

ROT = Path(__file__).resolve().parent
VENV = ROT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
KRAV = ROT / "requirements.txt"
MARKOR = VENV / ".spektro-krav"

# Körs med en annan Python: skriver versionen ("3.12") om den kan få färdiga paket, det vill säga 64-bitars, inte
# free-threaded och på Windows x64-bygget. Om just den versionen har färdiga paket avgör pip (--only-binary).
KOLLA = (
    "import sys, sysconfig\n"
    "ok = sys.maxsize > 2**32 and not sysconfig.get_config_var('Py_GIL_DISABLED')\n"
    "ok = ok and (sys.platform != 'win32' or sysconfig.get_platform() == 'win-amd64')\n"
    "print('%d.%d' % sys.version_info[:2] if ok else '')\n"
)

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

PROJEKT = "Grupp GRYb1  ·  Effektiva ljuskällor  ·  TFYY51 Ingenjörsprojekt, HT 2026"
TEAM = [
    ("Elias Holmberg", "Programmeringsansvarig", True),
    ("Adrian Lindstedt", "Labb, test och kvalitet", True),
    ("Alan Hosseini", "Projektledare", False),
    ("Isak Jansson", "Dokumentansvarig", False),
    ("Oscar Al-Ishak", "Design och optik", False),
]

MODULER = ["numpy", "cv2", "matplotlib.pyplot", "spectrometer.calc", "spectrometer.files", "spectrometer.source",
           "spectrometer.plot"]


def skriv(text):
    """Skriv text direkt till terminalen."""
    sys.stdout.write(text)
    sys.stdout.flush()


def skriv_rad(text="", farg=""):
    """Skriv en rad i färgen farg (koderna ovan) och återställ färgen efter."""
    skriv(f"{farg}{text}{NOLL}\n" if farg else f"{text}\n")


def las_flaggor():
    """Läs spektros egna flaggor; övriga lämnas till spectrometer.main."""
    tolk = argparse.ArgumentParser(
        prog="spektro",
        description="Startar spektrometern med startskärm i maximerat fönster.",
        epilog="Andra flaggor skickas vidare till spectrometer.main.",
        allow_abbrev=False,
    )
    tolk.add_argument("--windowed", action="store_true", help="maximera inte fönstret")
    tolk.add_argument("--no-splash", action="store_true", help="ingen startskärm, direkt till prompten")
    tolk.add_argument("--delay", type=float, default=PAUS_RAD, metavar="SEK",
                      help=f"paus mellan raderna i sekunder (standard {PAUS_RAD})")
    return tolk.parse_known_args()


def kor_tyst(kommando):
    """Kör kommando och fånga utskriften; text som inte går att avkoda blir ersättningstecken."""
    return subprocess.run([str(d) for d in kommando], capture_output=True, text=True, errors="replace")


def python_version(py):
    """Versionen ("3.12") om py går att köra och kan få färdiga paket, annars None."""
    try:
        return kor_tyst([py, "-c", KOLLA]).stdout.strip() or None
    except OSError:
        return None


def andra_pythons():
    """Andra installerade Python, nyaste först: py-launchern på Windows, python3.N i PATH annars."""
    if sys.platform == "win32":
        try:
            lista = kor_tyst(["py", "--list-paths"]).stdout
        except OSError:
            return []  # Python installerad utan py-launchern
        return re.findall(r"([A-Za-z]:\\.*?python\.exe)\s*$", lista, re.IGNORECASE | re.MULTILINE)
    namn = [f"python3.{n}" for n in range(20, 8, -1)] + ["python3"]
    return [sokvag for sokvag in map(shutil.which, namn) if sokvag]


def installera(summa):
    """Installera requirements.txt i .venv, bara färdiga paket. None om det gick, annars pips rad om paketet som
    saknar färdig version för den här Pythonen. Andra fel (till exempel inget nät) avslutar."""
    print("Installerar paketen i requirements.txt ...")
    svar = kor_tyst([VENV_PY, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--only-binary=:all:",
                     "-r", KRAV])
    if svar.returncode == 0:
        MARKOR.write_text(summa)
        return None
    saknas = [rad.strip() for rad in svar.stderr.splitlines() if "No matching distribution" in rad]
    if saknas:
        return saknas[-1]
    sys.exit(f"Kunde inte installera paketen i {VENV}:\n{svar.stderr.strip()}")


def ordna_miljon():
    """Se till att .venv finns, är byggd med en Python som kan få färdiga paket och har requirements.txt."""
    try:
        summa = hashlib.sha256(KRAV.read_bytes()).hexdigest()
        if Path(sys.prefix).resolve() == VENV.resolve():
            # körs redan i .venv (startaren har ordnat den): installera bara om requirements.txt ändrats
            if not MARKOR.exists() or MARKOR.read_text() != summa:
                saknas = installera(summa)
                if saknas:
                    sys.exit(f"Kunde inte installera paketen i {VENV}: {saknas}")
            return
        version = python_version(VENV_PY) if VENV_PY.exists() else None
        provade, saknas = set(), None
        if version:
            if MARKOR.exists() and MARKOR.read_text() == summa:
                return
            saknas = installera(summa)
            if not saknas:
                return
            provade.add(version)
            print(f"Python {version} i .venv saknar färdiga paket ({saknas}); letar efter en annan Python ...")
        elif VENV.exists():
            print("Miljön i .venv är byggd med en Python som inte går att använda: bygger om den ...")
        else:
            print("Första gången: bygger miljön i .venv ...")
        for py in [sys.executable, *andra_pythons()]:
            version = python_version(py)
            if not version or version in provade:
                continue  # fel sorts Python, eller en version som redan saknat paket
            provade.add(version)
            print(f"Bygger .venv med Python {version} ({py}) ...")
            subprocess.run([py, "-m", "venv", "--clear", str(VENV)], check=True)
            saknas = installera(summa)
            if not saknas:
                return
            print(f"Python {version} saknar färdiga paket ({saknas}); provar nästa ...")
    except (OSError, subprocess.CalledProcessError) as fel:
        tips = "\nPå Debian och Ubuntu behövs paketet python3-venv." if sys.platform.startswith("linux") else ""
        sys.exit(f"Kunde inte ordna miljön i {VENV}: {fel}{tips}")
    if sys.platform == "win32":
        hur = ('Installera en ny Python från python.org med "Windows installer (64-bit)" och kryssa i\n'
               '"Add python.exe to PATH". Kör sedan: py -m spektro')
    else:
        hur = "Installera en 64-bitars Python som paketen finns för och kör spektro med den."
    orsak = f"\nSenast saknades: {saknas}" if saknas else ""
    sys.exit(f"Hittade ingen Python på datorn som kan installera paketen utan att kompilera.{orsak}\n{hur}")


def kor_i_miljon():
    """Kör spektro.py igen med Python i .venv och avsluta med dess kod."""
    barn = subprocess.Popen([VENV_PY, ROT / "spektro.py", *sys.argv[1:]])
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
    # ctypes antar annars att fönstermarkörerna är heltal av fel storlek
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
    # Konsolen kan ligga i ett annat fönster (till exempel Windows Terminal): 4 = GW_OWNER, 3 = GA_ROOTOWNER
    egna_fonster = (konsol, u32.GetWindow(konsol, 4), u32.GetAncestor(konsol, 3))
    if fram not in egna_fonster:
        return  # fönstret i fokus är inte vårt: rör det inte
    u32.ShowWindow(fram, 3)  # 3 = SW_MAXIMIZE
    time.sleep(0.2)


def maximera_linux():
    """Maximera terminalfönstret med wmctrl eller xterm-koden."""
    if shutil.which("wmctrl"):
        subprocess.run(["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"], check=False)
    else:
        skriv("\x1b[9;1t")  # xterm-koden för maximera
    time.sleep(0.2)


def rensa():
    """Töm skärmen och rullningshistoriken."""
    skriv("\x1b[2J\x1b[3J\x1b[H")


def rita_prisma():
    """Rita färgprismat centrerat, med plats för prompten under."""
    from startskarm import prisma

    kolumner, rader = shutil.get_terminal_size((120, 40))
    bredd = max(20, min(kolumner - 2, max(4, rader - 22) * 4))
    hojd = max(5, round(bredd / 4))  # teckenceller ungefär dubbelt så höga
    vanster = " " * max(0, (kolumner - bredd) // 2)
    linjer = prisma.render("color", bredd, hojd)
    skriv("\n" + "\n".join(vanster + linje for linje in linjer) + "\n\n")


def gom_hjalpen():
    """Svälj det main skriver före första prompten (hjälpen); prismat och tipset står redan på skärmen."""
    ekta_input, ekta_ut = builtins.input, sys.stdout
    sys.stdout = io.StringIO()

    def forsta_input(prompt=""):
        """Släpp tillbaka utskriften och vanliga input när prompten visas första gången."""
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
        skriv_rad(f"    {namn:<18} {ansvar}", VIT if framhav else GRA)
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
            importlib.import_module(namn)
        time.sleep(PAUS_SLUT)
        skriv_info()
        skriv("\x1b[?25h")
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
