"""Kontrollerar att installationen räcker för spectrometer-programmet.

Kör i repots rot med .venv aktiv:

    python check_install.py
    python check_install.py --kamera 0
    python check_install.py --kamera 0 --bilder 5

Skriver en rad per kontroll, OK eller FEL, och sist "Installationen stämmer." (utgångskod 0)
eller en rad om hur många fel som fanns (utgångskod 1). Utan --kamera öppnas ingen kamera.
Filen använder bara standardbiblioteket; övriga bibliotek importeras först när de kontrolleras.
"""

import argparse
import importlib
import importlib.metadata
import re
import sys
from pathlib import Path

KRAV_PYTHON = (3, 12)
KRAVFILER = ("requirements.txt", "requirements-dev.txt")

# Pip-namn som inte är samma som importnamnet (normaliserade pip-namn).
IMPORTNAMN = {
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "opencv-contrib-python": "cv2",
    "opencv-contrib-python-headless": "cv2",
    "pillow": "PIL",
    "pyyaml": "yaml",
    "scikit-learn": "sklearn",
    "scikit-image": "skimage",
    "beautifulsoup4": "bs4",
    "python-dateutil": "dateutil",
    "pytest-cov": "pytest_cov",
}


class _SvenskFormatter(argparse.HelpFormatter):
    """Hjälpformaterare som skriver "användning:" i stället för "usage:"."""

    def add_usage(self, usage, actions, groups, prefix=None):
        """Lägger till användningsraden med svensk inledning."""
        if prefix is None:
            prefix = "användning: "
        super().add_usage(usage, actions, groups, prefix)


class _SvenskParser(argparse.ArgumentParser):
    """ArgumentParser som skriver felmeddelanden på svenska."""

    def error(self, message):
        """Skriver användningsraden och felet på svenska och avslutar med utgångskod 2."""
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: fel: {message}\n")


def _ok(text):
    """Ger en godkänd kontroll som (True, rad)."""
    return (True, "OK " + text)


def _fel(text, kolon=False):
    """Ger en underkänd kontroll som (False, rad). Filfel skrivs med FEL: enligt planen."""
    return (False, ("FEL: " if kolon else "FEL ") + text)


def _info(text):
    """Ger en varning som (True, rad): syns men räknas inte som fel."""
    return (True, text)


def _heltal(text):
    """Gör kommandoradens text till ett heltal, med ett svenskt felmeddelande om det inte går."""
    try:
        return int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"ska vara ett heltal, fick {text!r}") from None


def _bygg_parser():
    """Bygger kommandoradens flaggor med svensk hjälptext."""
    parser = _SvenskParser(
        prog="python check_install.py",
        description=(
            "Kontrollerar Python, .venv, biblioteken i requirements.txt och requirements-dev.txt, "
            "OpenCV:s kamerastöd och tkinter. Kör i repots rot med .venv aktiv. "
            "Med --kamera N öppnas dessutom kamera N och några bilder läses."
        ),
        formatter_class=_SvenskFormatter,
        add_help=False,
    )
    flaggor = parser.add_argument_group("flaggor")
    flaggor.add_argument("-h", "--help", action="help", help="visa den här hjälpen och avsluta")
    flaggor.add_argument(
        "--kamera",
        type=_heltal,
        metavar="N",
        help="öppna kamera N (samma tal som i 'source camera N') och läs bilder; "
        "utan flaggan öppnas ingen kamera",
    )
    flaggor.add_argument(
        "--bilder",
        type=_heltal,
        metavar="K",
        help="antal bilder att läsa med --kamera (standard: 3)",
    )
    return parser


def _kolla_python():
    """Kontrollerar att Python är 3.12."""
    v = sys.version_info
    text = f"Python {v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) == KRAV_PYTHON:
        return [_ok(text)]
    kravtext = f"{KRAV_PYTHON[0]}.{KRAV_PYTHON[1]}"
    return [_fel(f"{text}: projektet kräver Python {kravtext} (Windows: py -{kravtext} -m venv .venv)")]


def _kolla_venv():
    """Kontrollerar att en virtuell miljö är aktiv (sys.prefix skiljer sig från sys.base_prefix)."""
    if sys.prefix == sys.base_prefix:
        return [_fel(".venv är inte aktiv: sys.prefix är Pythons egen mapp. "
                     "Linux: source .venv/bin/activate. Windows: .\\.venv\\Scripts\\Activate.ps1")]
    namn = Path(sys.prefix).name
    if namn == ".venv":
        return [_ok(f".venv aktiv ({sys.prefix})")]
    return [_ok(f"virtuell miljö aktiv ({sys.prefix}). OBS: mappen heter {namn}, projektet använder .venv")]


def _les_krav(fil):
    """Läser en requirements-fil som utf-8-sig. Ger (paketnamn, None) eller ([], felrad)."""
    if not fil.is_file():
        return [], _fel(f"{fil.name} saknas i {fil.parent}", kolon=True)
    rader = fil.read_bytes()
    if rader.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in rader:
        return [], _fel(
            f"{fil.name} är UTF-16 (PowerShell 5.1 skriver så med > och >>). "
            "Spara om den som UTF-8 i VS Code.",
            kolon=True,
        )
    try:
        text = rader.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], _fel(f"{fil.name} går inte att läsa som UTF-8. Spara om den som UTF-8 i VS Code.",
                        kolon=True)
    namn = []
    for rad in text.splitlines():
        rad = rad.split("#", 1)[0].strip()
        if not rad or rad.startswith("-"):
            continue
        traff = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", rad)
        if traff:
            namn.append(traff.group(0))
    return namn, None


def _normalisera(namn):
    """Pip-namn på jämförbar form: gemener, med - i stället för _ och ."""
    return re.sub(r"[-_.]+", "-", namn).lower()


def _kolla_paket(namn):
    """Importerar ett paket från requirements och ger OK med version eller FEL."""
    norm = _normalisera(namn)
    modul = IMPORTNAMN.get(norm, norm.replace("-", "_"))
    try:
        mod = importlib.import_module(modul)
    except ModuleNotFoundError as fel:
        try:
            version = importlib.metadata.version(namn)
        except importlib.metadata.PackageNotFoundError:
            return _fel(f"{namn}: saknas ({fel}). Kör: python -m pip install -r requirements.txt "
                        "-r requirements-dev.txt")
        return _ok(f"{namn} {version} (installerat, men ingen modul {modul} att importera)")
    except (ImportError, OSError, RuntimeError, AttributeError) as fel:
        return _fel(f"{namn}: går inte att importera ({type(fel).__name__}: {fel})")
    try:
        version = importlib.metadata.version(namn)
    except importlib.metadata.PackageNotFoundError:
        version = getattr(mod, "__version__", "okänd version")
    return _ok(f"{namn} {version}")


def _kolla_krav():
    """Kontrollerar alla paket i requirements-filerna, en rad per paket och en FEL: per filfel."""
    mapp = Path(__file__).resolve().parent
    rader = []
    sedda = set()
    for filnamn in KRAVFILER:
        namn, filfel = _les_krav(mapp / filnamn)
        if filfel is not None:
            rader.append(filfel)
            continue
        for paket in namn:
            norm = _normalisera(paket)
            if norm in sedda:
                continue
            sedda.add(norm)
            rader.append(_kolla_paket(paket))
    return rader


def _backendnamn_ur_bygginfo(info):
    """Plockar kamerabackend ur cv2.getBuildInformation() när videoio_registry saknas."""
    namn = []
    for monster, visas in (
        (r"v4l/v4l2\s*:\s*YES", "V4L2"),
        (r"DirectShow\s*:\s*YES", "DSHOW"),
        (r"Media Foundation\s*:\s*YES", "MSMF"),
        (r"AVFoundation\s*:\s*YES", "AVFOUNDATION"),
    ):
        if re.search(monster, info):
            namn.append(visas)
    return namn


def _kolla_kamerastod():
    """Kontrollerar att OpenCV har ett kamerabackend, och det som source.py väljer på det här systemet."""
    try:
        import cv2
    except (ImportError, OSError, RuntimeError, AttributeError) as fel:
        return [_fel(f"OpenCV-kamerastöd: cv2 går inte att importera ({type(fel).__name__}: {fel})")]
    try:
        from cv2 import videoio_registry

        namn = [videoio_registry.getBackendName(b) for b in videoio_registry.getCameraBackends()]
        kalla = "videoio_registry"
    except (ImportError, AttributeError, cv2.error):
        namn = _backendnamn_ur_bygginfo(cv2.getBuildInformation())
        kalla = "getBuildInformation"
    if not namn:
        return [_fel(f"OpenCV-kamerastöd: inget kamerabackend ({kalla}). "
                     "Installera opencv-python enligt requirements.txt.")]
    if sys.platform.startswith("linux"):
        behovs = "V4L2"
    elif sys.platform == "win32":
        behovs = "DSHOW"
    else:
        behovs = None
    if behovs is not None and behovs not in namn:
        return [_fel(f"OpenCV-kamerastöd: {', '.join(namn)}, men source.py väljer {behovs} här")]
    return [_ok(f"OpenCV-kamerastöd: {', '.join(namn)} (cv2 {cv2.__version__})")]


def _kolla_tkinter():
    """Kontrollerar att tkinter går att importera (matplotlib använder det för fönstret)."""
    try:
        import tkinter
    except (ImportError, OSError, RuntimeError) as fel:
        return [_fel(f"tkinter: går inte att importera ({type(fel).__name__}: {fel}). "
                     "Arch: sudo pacman -S tk. Windows: installera om Python med tcl/tk.")]
    return [_ok(f"tkinter (Tk {tkinter.TkVersion})")]


def _forsta_bilden_morkare(medel):
    """Sant om första bildens medelvärde ligger under de senares hela spann, mätt med deras eget spann.

    medel: medelvärdena per bild, första först, minst tre. Gränsen är de senares minsta medel minus
    deras spann (störst minus minst), så den följer kamerans eget brus och har inget fast tal.
    """
    senare = medel[1:]
    spann = max(senare) - min(senare)
    return medel[0] < min(senare) - spann


def _kolla_kamera(nummer, antal):
    """Öppnar kamera N via spectrometer.source, läser antal bilder och släpper alltid kameran."""
    rader = []
    try:
        from spectrometer.source import close_source, open_source, read_frame
    except (ImportError, OSError, RuntimeError, AttributeError) as fel:
        return [_fel(f"kamera {nummer}: spectrometer.source går inte att importera "
                     f"({type(fel).__name__}: {fel}). Kör i repots rot.")]
    src = None
    try:
        try:
            src = open_source("camera", nummer)
        except (RuntimeError, ValueError, OSError) as fel:
            return [_fel(f"kamera {nummer}: {fel}")]
        rader.append(_ok(f"kamera {nummer} öppnad"))
        medel = []
        for i in range(1, antal + 1):
            try:
                bild = read_frame(src)
            except (RuntimeError, ValueError, OSError) as fel:
                rader.append(_fel(f"kamera {nummer}: bild {i} gick inte att läsa ({fel})"))
                break
            medel.append(float(bild.mean()))
            rader.append(_ok(
                f"bild {i}: form {bild.shape}, dtype {bild.dtype}, max {bild.max()}, "
                f"medel {medel[-1]:.2f}"
            ))
        if len(medel) == antal and antal >= 3:
            if _forsta_bilden_morkare(medel):
                senare = ", ".join(f"{m:.2f}" for m in medel[1:])
                rader.append(_info(
                    f"OBS: mörk första bild (medel {medel[0]:.2f} mot {senare} i de senare). "
                    "Kameran behöver värmas upp: läs bort första bilden eller mät en gång till."
                ))
        elif len(medel) == antal:
            rader.append(_info("OBS: för få bilder för att avgöra om första bilden är mörk "
                               "(använd --bilder 3 eller fler)."))
    finally:
        if src is not None:
            close_source(src)
    return rader


def main(argv=None):
    """Kör kontrollerna, skriver en rad per kontroll och ger utgångskod 0 (stämmer) eller 1 (fel)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = _bygg_parser()
    args = parser.parse_args(argv)
    if args.bilder is not None and args.kamera is None:
        parser.error("--bilder hör ihop med --kamera N")
    antal_bilder = 3 if args.bilder is None else args.bilder
    if antal_bilder < 1:
        parser.error("--bilder måste vara minst 1")

    resultat = []
    resultat += _kolla_python()
    resultat += _kolla_venv()
    resultat += _kolla_krav()
    resultat += _kolla_kamerastod()
    resultat += _kolla_tkinter()
    if args.kamera is not None:
        resultat += _kolla_kamera(args.kamera, antal_bilder)

    for _, rad in resultat:
        print(rad)
    antal_fel = sum(1 for ok, _ in resultat if not ok)
    if antal_fel == 0:
        print("Installationen stämmer.")
        return 0
    print(f"Installationen stämmer inte: {antal_fel} fel ovan.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
