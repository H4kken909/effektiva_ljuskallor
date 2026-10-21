"""Kontrollerar installationen: Python, .venv, biblioteken, kamerastödet i OpenCV och Tk.

Körs i projektmappen med .venv aktiv:
  python check_install.py
  python check_install.py --kamera N [--bilder K]    provar kameran N med K bilder (standard 3)
Varje rad börjar med OK, INFO, VARNING eller FEL. Slutkod 0 om inget är FEL (VARNING räknas som ok), annars 1.
"""

import importlib.metadata
import os
import platform
import re
import sys
import sysconfig
from pathlib import Path

ROT = Path(__file__).resolve().parent
OPENCV = ("opencv-python", "opencv-python-headless")  # något av dem duger, båda ger modulen cv2
INSTALLERA = "Kör: uv pip install -r requirements.txt -r requirements-dev.txt"
TK_ATGARD = (
    "Arch: sudo pacman -S tk. Debian: sudo apt install python3-tk. Windows: installera om Python och ta med tcl/tk."
)


def delar(version):
    """Versionen som tal: "2.5.4" ger [2, 5, 4]; text som rc1 räknas som 0."""
    return [int(re.match(r"\d*", bit).group() or 0) for bit in version.split(".")]


def jamfor(krav, installerad):
    """Ger "OK" om versionerna är lika, "VARNING" om bara patchnivån (tredje talet och framåt) skiljer, annars "FEL"."""
    a, b = delar(krav), delar(installerad)
    langd = max(len(a), len(b), 3)
    a += [0] * (langd - len(a))
    b += [0] * (langd - len(b))
    if a == b:
        return "OK"
    return "VARNING" if a[:2] == b[:2] else "FEL"


def version_av(namn):
    """Installerad version av biblioteket namn, eller None om det inte är installerat."""
    try:
        return importlib.metadata.version(namn)
    except importlib.metadata.PackageNotFoundError:
        return None


def installerad(namn):
    """Ger (namnet som hittades, version). För OpenCV duger opencv-python eller opencv-python-headless."""
    for kandidat in OPENCV if namn.lower() in OPENCV else (namn,):
        version = version_av(kandidat)
        if version is not None:
            return kandidat, version
    return namn, None


def lasa_krav(fil):
    """Läser en requirements-fil som UTF-8 (med eller utan BOM). Ger [(namn, version eller None)].

    Fel: ValueError om filen inte är UTF-8, till exempel sparad som UTF-16 av PowerShell.
    """
    try:
        text = fil.read_text(encoding="utf-8-sig")
        if "\x00" in text:
            raise UnicodeError("NUL-tecken: UTF-16 utan BOM")
    except UnicodeError as error:
        raise ValueError(
            f"{fil.name} är inte sparad som UTF-8 (UTF-16 från PowerShell?). Spara om den som UTF-8."
        ) from error
    krav = []
    for rad in text.splitlines():
        rad = rad.split("#")[0].strip()
        traff = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:==\s*([^\s;]+))?", rad)
        if rad and not rad.startswith("-") and traff:
            krav.append((traff.group(1), traff.group(2)))
    return krav


def kolla_python(rot):
    """Jämför Python med .python-version och ser att .venv i projektmappen är aktiv."""
    rader = []
    fil = rot / ".python-version"
    nu = platform.python_version()
    if not fil.is_file():
        rader.append(("INFO", f"Python {nu} (ingen .python-version att jämföra med)"))
    else:
        onskad = fil.read_text(encoding="utf-8-sig").strip()
        delar_onskad = onskad.split(".")
        if nu.split(".")[: len(delar_onskad)] == delar_onskad:
            rader.append(("OK", f"Python {nu}"))
        else:
            rader.append(("FEL", f"Python är {nu} men .python-version säger {onskad}. Kör: uv python install {onskad}"))
    if Path(sys.prefix).resolve() == (rot / ".venv").resolve():
        rader.append(("OK", "miljön är .venv i projektmappen"))
    else:
        rader.append(("FEL", f"miljön är {sys.prefix} (ska vara .venv i projektmappen). Aktivera .venv och kör igen."))
    return rader


def kolla_bibliotek(rot):
    """Jämför varje bibliotek i requirements-filerna med det installerade. Ger resultatrader."""
    rader = []
    for namn, kravs in (("requirements.txt", True), ("requirements-dev.txt", False)):
        fil = rot / namn
        if not fil.is_file():
            rader.append(("FEL" if kravs else "INFO", f"{namn} saknas i {rot}"))
            continue
        try:
            krav = lasa_krav(fil)
        except ValueError as error:
            rader.append(("FEL", str(error)))
            continue
        for bibliotek, version in krav:
            hittat, har = installerad(bibliotek)
            if har is None:
                rader.append(("FEL", f"{bibliotek} är inte installerat. {INSTALLERA}"))
            elif version is None:
                rader.append(("OK", f"{hittat} {har} (ingen version i {namn})"))
            else:
                niva = jamfor(version, har)
                if niva == "OK":
                    rader.append(("OK", f"{hittat} {har}"))
                elif niva == "VARNING":
                    rader.append(
                        (niva, f"{hittat} {har} är installerat, {namn} har {version} (bara patchnivån skiljer)")
                    )
                else:
                    rader.append((niva, f"{hittat} {har} är installerat, {namn} har {version}. {INSTALLERA}"))
    if all(version_av(namn) for namn in OPENCV):
        rader.append(
            ("VARNING", "opencv-python och opencv-python-headless är båda installerade och krockar. "
                        "Avinstallera båda, installera om.")
        )
    return rader


def kamerabackend(cv2):
    """Ger (backend, namn): V4L2 på Linux, DirectShow (DSHOW) på Windows, annars (CAP_ANY, None)."""
    if sys.platform.startswith("linux"):
        return cv2.CAP_V4L2, "V4L2"
    if sys.platform == "win32":
        return cv2.CAP_DSHOW, "DirectShow"
    return cv2.CAP_ANY, None


def kolla_opencv():
    """Ser att OpenCV har kamerastöd för systemet: V4L2 på Linux, DirectShow på Windows."""
    try:
        import cv2
    except ImportError as error:
        return [("FEL", f"cv2 går inte att importera ({error}). {INSTALLERA}")]
    backend, namn = kamerabackend(cv2)
    if namn is None:
        return [("INFO", f"OpenCV {cv2.__version__}; kamerastödet kontrolleras bara på Linux och Windows")]
    if backend in cv2.videoio_registry.getBackends():
        return [("OK", f"OpenCV {cv2.__version__} har {namn}")]
    return [("FEL", f"OpenCV {cv2.__version__} saknar {namn}. Avinstallera OpenCV och installera om.")]


def kolla_tk():
    """Skapar ett Tk-fönster och släpper det (matplotlib ritar med Tk). Ingen skärm (SSH) är VARNING, ingen Tk FEL."""
    try:
        import tkinter
    except ImportError:
        return [("FEL", f"tkinter saknas. {TK_ATGARD}")]
    try:
        tkinter.Tk().destroy()
    except tkinter.TclError as error:
        if "display" in str(error):
            return [("VARNING", f"Tk hittar ingen skärm ({error}). Väntat över SSH; fönster går inte att öppna här.")]
        return [("FEL", f"Tk startar inte ({error}). {TK_ATGARD}")]
    return [("OK", "Tk (tkinter) öppnar ett fönster")]


def arm_emulering(python_plattform, maskin, miljo):
    """Sant när x64-Python (win-amd64) körs på en ARM64-dator. Antaget: Windows visar ARM64 i PROCESSOR_ARCHITEW6432."""
    dator = (miljo.get("PROCESSOR_ARCHITEW6432") or maskin).upper()
    return python_plattform == "win-amd64" and dator == "ARM64"


def kolla_arkitektur():
    """En INFO-rad om Python är x64 men datorn är ARM64; annars ingen rad."""
    if arm_emulering(sysconfig.get_platform(), platform.machine(), os.environ):
        return [("INFO", "Python är x64 men datorn är ARM64 (emulering): kameran är oprövad")]
    return []


def kor_alla(rot):
    """Kör alla kontroller i projektmappen rot. Ger resultatraderna i ordning."""
    return kolla_python(rot) + kolla_bibliotek(rot) + kolla_opencv() + kolla_tk() + kolla_arkitektur()


def kolla_kamera(index, antal):
    """Öppnar kamera index, läser antal bilder och ger en rad per bild med storleken. Varnar om första är mörk."""
    try:
        import cv2
    except ImportError as error:
        return [("FEL", f"cv2 går inte att importera ({error}). {INSTALLERA}")]
    cap = cv2.VideoCapture(index, kamerabackend(cv2)[0])
    if not cap.isOpened():
        cap.release()
        text = (f"camera.open_failed: kunde inte öppna kamera {index}. "
                "Stäng program som håller kameran eller prova ett annat index.")
        return [("FEL", text)]
    rader = []
    medel = []
    try:
        for nr in range(1, antal + 1):
            ok, bild = cap.read()
            if not ok or bild is None:
                rader.append(("FEL", f"camera.read_failed: bild {nr} kunde inte läsas"))
                break
            medel.append(float(bild.mean()))
            rader.append(("OK", f"bild {nr}: {bild.shape[1]} x {bild.shape[0]}, medelvärde {medel[-1]:.1f}"))
    finally:
        cap.release()
    if len(medel) > 1 and medel[0] < 0.5 * max(medel[1:]):
        rader.append(("INFO", "OBS mörk första bild: kameran behöver några bilder för att värmas upp"))
    return rader


def lasa_argument(argv):
    """Läser --kamera N och --bilder K. Ger (kamera eller None, antal bilder).

    Fel: ValueError med en rad på svenska vid en okänd flagga eller ett värde som inte är ett heltal.
    """
    varden = {"--kamera": None, "--bilder": "3"}
    rest = list(argv)
    while rest:
        flagga = rest.pop(0)
        if flagga not in varden or not rest:
            raise ValueError(f"använd: python check_install.py [--kamera N [--bilder K]] (fick {flagga})")
        varden[flagga] = rest.pop(0)
    try:
        kamera = None if varden["--kamera"] is None else int(varden["--kamera"])
        bilder = int(varden["--bilder"])
    except ValueError as error:
        raise ValueError("--kamera och --bilder ska följas av ett heltal") from error
    if (kamera is not None and kamera < 0) or bilder < 1:
        raise ValueError("--kamera ska vara minst 0 och --bilder minst 1")
    return kamera, bilder


def visa(rader):
    """Skriver raderna som NIVÅ  text och ger antalet FEL."""
    for niva, text in rader:
        print(f"{niva}  {text}")
    return sum(1 for niva, _ in rader if niva == "FEL")


def main(argv=None):
    """Kör kontrollerna eller kameraprovet och skriver slutraden. Ger slutkoden: 0 om inget är FEL, annars 1."""
    try:
        kamera, bilder = lasa_argument(sys.argv[1:] if argv is None else argv)
    except ValueError as error:
        print(f"FEL  {error}")
        return 1
    if kamera is not None:
        return 1 if visa(kolla_kamera(kamera, bilder)) else 0
    antal = visa(kor_alla(ROT))
    if antal:
        print(f"Installationen stämmer inte: {antal} fel. Rätta FEL-raderna och kör igen.")
        return 1
    print("Installationen stämmer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())