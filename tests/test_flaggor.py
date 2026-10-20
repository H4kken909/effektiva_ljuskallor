"""1.0.34 Startflaggor: --version, --kor FIL med och utan --avsluta, --camera, --input, --output och spektro-start.txt."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from spectrometer import __version__, main

ROT = Path(__file__).resolve().parents[1]
FORSTA_RADEN = "Skriv help för kommandona. quit eller Ctrl+D avslutar."


def prompt_lines(monkeypatch, lines, tty=False):
    """input ger raderna i lines och sedan EOF (Ctrl+D); tty bestämmer vad sys.stdin.isatty() svarar."""
    feed = iter(lines)

    def fake_input(prompt):
        item = next(feed, None)
        if item is None:
            raise EOFError
        return item

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: tty)


def no_prompt(monkeypatch):
    """input får inte anropas: med --avsluta ska prompten aldrig visas."""
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("prompten visades"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)


def command_file(tmp_path, text):
    """Skriver kommandofilen fil.txt i tmp_path och ger sökvägen med snedstreck framåt."""
    path = tmp_path / "fil.txt"
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def starta(tmp_path, *flaggor):
    """Startar det riktiga programmet med flaggorna och tom stdin. Ger (slutkod, stdout, stderr)."""
    miljo = {**os.environ, "PYTHONPATH": str(ROT), "PYTHONUTF8": "1", "MPLBACKEND": "Agg"}
    korning = subprocess.run([sys.executable, *flaggor], input=b"", capture_output=True, cwd=tmp_path, env=miljo,
                             timeout=120)
    return korning.returncode, korning.stdout.decode("utf-8"), korning.stderr.decode("utf-8")


def test_version_flag(capsys):
    """FLA-01, FLA-02: --version skriver spektro och versionen ur spectrometer/__init__.py och avslutar med 0."""
    with pytest.raises(SystemExit) as done:
        main.main(["--version"])
    assert done.value.code == 0
    assert capsys.readouterr().out == f"spektro {__version__}\n"


def test_kor_avsluta_gives_0_or_1(monkeypatch, tmp_path, capsys):
    """FLA-05: --kor FIL --avsluta kör filen utan prompt och utan första raden; slutkod 0, eller 1 vid Fel:."""
    no_prompt(monkeypatch)
    path = command_file(tmp_path, "frames 2\nshow\n")
    assert main.main(["--kor", path, "--avsluta"]) == 0
    rows = capsys.readouterr().out.splitlines()
    assert rows[:3] == [f"Kör {path}", "spektro> frames 2", "frames: 2"]
    assert FORSTA_RADEN not in rows
    path = command_file(tmp_path, "frames tre\nframes 3\n")
    assert main.main(["--kor", path, "--avsluta"]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"Fel: input.invalid_argument: N ska vara ett heltal, fick tre ({path} rad 1)"
    )


def test_kor_then_prompt(monkeypatch, tmp_path, capsys):
    """FLA-04: utan --avsluta kommer prompten efter filen, med det filen ställde in."""
    prompt_lines(monkeypatch, ["show"])
    path = command_file(tmp_path, "frames 2\n")
    assert main.main(["--kor", path]) == 0
    rows = capsys.readouterr().out.splitlines()
    assert rows[:2] == [FORSTA_RADEN, f"Kör {path}"]
    assert "frames: 2" in rows


def test_quit_in_kor_file_ends_the_program(monkeypatch, tmp_path, capsys):
    """quit i --kor-filen avslutar programmet direkt, utan prompt."""
    no_prompt(monkeypatch)
    path = command_file(tmp_path, "quit\n")
    assert main.main(["--kor", path]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "Avslutar."


def test_source_and_output_flags(monkeypatch, tmp_path, capsys):
    """FLA-06, FLA-07, FLA-08, KAM-29: --camera, --input och --output sätter källan och output_dir utan utskrift."""
    no_prompt(monkeypatch)
    path = command_file(tmp_path, "show\n")
    main.main(["--input", "bild.png", "--output", "ut", "--kor", path, "--avsluta"])
    rows = capsys.readouterr().out.splitlines()
    assert "källa: fil bild.png" in rows
    assert "output_dir: ut" in rows
    main.main(["--camera", "2", "--kor", path, "--avsluta"])
    rows = capsys.readouterr().out.splitlines()
    assert rows[:2] == [f"Kör {path}", "spektro> show"]
    assert "källa: kamera 2" in rows


@pytest.mark.parametrize("tty", [True, False])
def test_start_file_only_in_a_terminal(tty, monkeypatch, tmp_path, capsys):
    """FLA-10: spektro-start.txt i arbetsmappen körs före första prompten, men bara när stdin är en terminal."""
    (tmp_path / "spektro-start.txt").write_text("# riggen\nframes 4\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    prompt_lines(monkeypatch, ["show"], tty)
    assert main.main([]) == 0
    rows = capsys.readouterr().out.splitlines()
    assert ("Kör spektro-start.txt" in rows) is tty
    assert ("frames: 4" in rows) is tty


def test_flags_through_the_real_program(tmp_path):
    """FLA-17, FLA-05: python -m spectrometer --version; fel flagga och --avsluta utan --kor ger slutkod 2 (argparse)."""
    kod, ut, _ = starta(tmp_path, "-m", "spectrometer", "--version")
    assert (kod, ut) == (0, f"spektro {__version__}\n")
    kod, _, fel = starta(tmp_path, "-m", "spectrometer.main", "--foo")
    assert kod == 2
    assert "unrecognized arguments: --foo" in fel
    kod, _, fel = starta(tmp_path, "-m", "spectrometer.main", "--avsluta")
    assert kod == 2
    assert "--avsluta kräver --kor FIL" in fel
    kod, _, _ = starta(tmp_path, "-m", "spectrometer.main", "--camera", "1", "--input", "bild.png")
    assert kod == 2
