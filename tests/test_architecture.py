"""Arkitekturreglerna: vem som får importera vem, vem som får skriva ut, och att funktioner går att ta bort."""

import ast
from pathlib import Path

import pytest

PAKET = Path(__file__).resolve().parents[1] / "spectrometer"

# En modul får bara importera moduler i ett lägre lager. Ny modul: lägg till den här först.
LAGER = {
    "out": 0, "theme": 0, "calc": 0,
    "session": 1, "quality": 1, "peaks": 1, "source": 1, "files": 1, "plot": 1, "roi": 1,
    "registry": 2, "measure": 2, "analysis": 2, "display": 2, "meta": 2,
    "commands": 3, "analys": 3,
    "main": 4, "__main__": 5,
}
BARA = {"matplotlib": {"plot", "analysis"}, "cv2": {"source", "files"}}
MODULER = [
    (f.relative_to(PAKET).parts[0].removesuffix(".py"), f)
    for f in sorted(PAKET.rglob("*.py"))
    if f.relative_to(PAKET).parts != ("__init__.py",)
]
IDS = [f.relative_to(PAKET).as_posix() for _, f in MODULER]


def importer(fil):
    """Varje import i filen som namnlista, t.ex. ["spectrometer", "calc"] eller ["numpy"]."""
    for nod in ast.walk(ast.parse(fil.read_text(encoding="utf-8"))):
        if isinstance(nod, ast.Import):
            for alias in nod.names:
                yield alias.name.split(".")
        elif isinstance(nod, ast.ImportFrom):
            assert nod.level == 0, f"{fil.name}: relativ import, skriv from spectrometer import ..."
            if nod.module == "spectrometer":
                for alias in nod.names:
                    yield ["spectrometer", alias.name]
            else:
                yield nod.module.split(".")


@pytest.mark.parametrize(("namn", "fil"), MODULER, ids=IDS)
def test_importer_gar_nedat(namn, fil):
    """Projektmoduler bara från lägre lager; matplotlib och cv2 bara där BARA tillåter."""
    assert namn in LAGER, f"{namn} saknas i LAGER"
    for delar in importer(fil):
        if delar[0] == "spectrometer" and len(delar) > 1 and delar[1] != "__version__":
            assert delar[1] in LAGER, f"{fil.name} importerar okänd modul {delar[1]}"
            assert LAGER[delar[1]] < LAGER[namn], f"{fil.name} ({namn}) får inte importera {delar[1]}"
        elif delar[0] in BARA:
            assert namn in BARA[delar[0]], f"{fil.name} får inte använda {delar[0]}"


@pytest.mark.parametrize(("namn", "fil"), MODULER, ids=IDS)
def test_bara_out_skriver_ut(namn, fil):
    """print finns bara i out.py."""
    if namn == "out":
        return
    for nod in ast.walk(ast.parse(fil.read_text(encoding="utf-8"))):
        if isinstance(nod, ast.Call) and isinstance(nod.func, ast.Name):
            assert nod.func.id != "print", f"{fil.name} rad {nod.lineno}: print, använd out.say"


def test_varje_funktion_gar_att_ta_bort():
    """Registret byggs utan var och en av kommandomodulerna; help och quit finns alltid kvar."""
    from spectrometer import commands, registry

    for bort in commands.FEATURES[1:]:
        registry.load(commands.modules([f for f in commands.FEATURES if f != bort]))
        assert {"help", "quit"} <= registry.COMMANDS.keys()


def test_help_ordningen():
    """help i samma ordning som i v1.0.0 (facit_04)."""
    from spectrometer import commands, registry

    registry.load(commands.modules())
    assert list(registry.COMMANDS) == [
        "help", "quit", "show", "status", "version", "source", "roi", "channel", "axis", "frames", "info", "cameras", "snap", "image",
        "step", "save", "start", "stability", "perf", "calibrate", "toppar", "dark", "response", "reference", "mode",
        "run", "wait", "reset", "undo", "history", "history save", "clear", "set", "rows", "background", "response save", "response load", "rigg",
        "theme",
        "view", "graf", "roi show", "roi auto", "roi profile", "roi band", "roi move", "axis detect",
        "exposure", "gain", "auto",
        "note", "series start", "series note", "series stop", "series plot",
        "load", "fwhm", "compare", "figure",
        "color", "mix", "bandgap", "repeat", "linearity", "calibrate save",
        "guide", "pause", "help limits",
    ]
