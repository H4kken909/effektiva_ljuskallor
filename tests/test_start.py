"""Start och avslut: slutkoden, UTF-8 i rör och att programmet startar under olika kodsidor (R14)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from spectrometer import main

ROT = Path(__file__).resolve().parents[1]
FORSTA_RADEN = "Skriv help för kommandona. quit eller Ctrl+D avslutar."


def starta(tmp_path, indata, kodning="utf-8"):
    """Startar det riktiga programmet med indata på stdin och PYTHONIOENCODING=kodning. Ger (slutkod, stdout-rader)."""
    miljo = {**os.environ, "PYTHONPATH": str(ROT), "PYTHONIOENCODING": kodning, "MPLBACKEND": "Agg"}
    miljo.pop("PYTHONUTF8", None)  # annars vinner PYTHONUTF8 över kodsidan och provet visar ingenting
    korning = subprocess.run(
        [sys.executable, "-m", "spectrometer.main"],
        input=indata.encode("utf-8"),
        capture_output=True,
        cwd=tmp_path,
        env=miljo,
        timeout=120,
    )
    return korning.returncode, korning.stdout.decode("utf-8").splitlines()


def run_prompt(monkeypatch, lines, tty):
    """Kör main med raderna vid prompten; tty bestämmer vad sys.stdin.isatty() svarar."""
    feed = iter(lines)

    def fake_input(prompt):
        return next(feed, "quit")

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(sys, "argv", ["spectrometer.main"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: tty)
    return main.main()


@pytest.mark.parametrize("kodning", ["utf-8", "cp1252"])
def test_start_ger_slutkod_0_och_forsta_raden(tmp_path, kodning):
    """help och quit under båda kodsidorna: slutkod 0 och första raden som i facit (ö kommer som UTF-8)."""
    kod, rader = starta(tmp_path, "help\nquit\n", kodning)
    assert kod == 0
    assert rader[0] == FORSTA_RADEN
    assert rader[-1].endswith("Avslutar.")  # prompten spektro> står på samma rad när indata är ett rör


def test_tom_stdin_ger_slutkod_0(tmp_path):
    """Ingenting på stdin (Ctrl+D direkt) är ett normalt avslut."""
    kod, rader = starta(tmp_path, "")
    assert kod == 0
    assert rader[0] == FORSTA_RADEN


def test_fel_i_en_kommandofil_ger_slutkod_1(tmp_path):
    """Ett kommando som ger Fel: när stdin är ett rör: slutkod 1, men raderna efter körs ändå."""
    kod, rader = starta(tmp_path, "foo\nhelp\nquit\n")
    assert kod == 1
    assert any("Fel: input.invalid_argument: okänt kommando foo" in rad for rad in rader)
    assert rader[-1].endswith("Avslutar.")


def test_stdin_las_som_utf8_aven_under_cp1252(tmp_path):
    """Ett ö på stdin når kommandot oförändrat: reconfigure gör stdin till UTF-8."""
    kod, rader = starta(tmp_path, "mätning\nquit\n", "cp1252")
    assert kod == 1
    assert any("okänt kommando mätning." in rad for rad in rader)


def test_interaktivt_ar_slutkoden_0_trots_fel(monkeypatch):
    """Vid en terminal (isatty sant) ger Fel: ingen slutkod; i ett rör ger det 1."""
    assert run_prompt(monkeypatch, ["foo", "quit"], tty=True) == 0
    assert run_prompt(monkeypatch, ["foo", "quit"], tty=False) == 1
    assert run_prompt(monkeypatch, ["show", "quit"], tty=False) == 0