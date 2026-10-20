"""1.0.33 Kommandofiler: run FIL, kommentarer med #, fel med radnummer, rekursion, quit i en fil, wait och exempel/."""

import shutil
from pathlib import Path

import cv2
import pytest
from test_elias import error_text, line_image, new_state, run_prompt

from spectrometer import registry
from spectrometer.commands import files_cmds

ROT = Path(__file__).resolve().parents[1]


def command_file(tmp_path, text, name="fil.txt"):
    """Skriver en kommandofil i tmp_path och ger sökvägen med snedstreck framåt."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def test_run_file(tmp_path, capsys):
    """KOM-01, KOM-02, KOM-03: raderna i ordning, spektro> RAD före svaret, tomma rader, # och inklistrad prompt."""
    image = tmp_path / "bild.png"
    cv2.imwrite(str(image), line_image())
    path = command_file(tmp_path, f"source file {image.as_posix()}\n\n# en kommentar\nroi 10 0 3 2  # remsan\nspektro> step\n")
    state = new_state()
    registry.run_command(state, f"run {path}")
    assert capsys.readouterr().out.splitlines() == [
        f"spektro> source file {image.as_posix()}",
        f"source file {image.as_posix()}",
        "spektro> roi 10 0 3 2  # remsan",
        "ROI:n kontrolleras vid nästa mätning.",
        "roi 10 0 3 2",
        "spektro> step",
        "Topp 200 vid pixel 12 (1 bild)",
    ]
    assert state["settings"]["roi"] == (10, 0, 3, 2)
    assert state["spectrum"] is not None


def test_run_stops_at_error(tmp_path):
    """KOM-02: första felet stoppar filen och får (FIL rad N) sist; raderna efter körs inte."""
    path = command_file(tmp_path, "frames 2\nframes tre\nframes 3\n")
    state = new_state()
    text = error_text(state, f"run {path}")
    assert text == f"input.invalid_argument: N ska vara ett heltal, fick tre ({path} rad 2)"
    assert state["settings"]["frames"] == 2


def test_run_missing_file(tmp_path):
    """En fil som saknas ger ett fel och ändrar ingenting; run utan FIL säger vad som saknas."""
    state = new_state()
    assert error_text(state, f"run {(tmp_path / 'finns_inte.txt').as_posix()}").startswith("[Errno 2]")
    assert error_text(state, "run") == "input.invalid_argument: run: FIL saknas"
    assert state["settings"] == new_state()["settings"]


def test_run_recursion(tmp_path):
    """KOM-04: en fil som kör sig själv stannar efter fem nivåer, med filen och raden en gång."""
    inner = command_file(tmp_path, "frames 2\n", "inre.txt")
    outer = command_file(tmp_path, f"run {inner}\n", "yttre.txt")
    itself = (tmp_path / "sig_sjalv.txt").as_posix()
    command_file(tmp_path, f"run {itself}\n", "sig_sjalv.txt")
    state = new_state()
    assert error_text(state, f"run {outer}") is None
    assert state["settings"]["frames"] == 2
    text = error_text(state, f"run {itself}")
    assert text == f"input.invalid_argument: run: för många nivåer (högst 5) ({itself} rad 1)"
    assert files_cmds._depth == 0


def test_run_quit_ends_the_program(monkeypatch, capsys, tmp_path):
    """KOM-04: quit i en fil avslutar hela programmet; raderna efter quit och prompten efter run kommer inte."""
    path = command_file(tmp_path, "frames 2\nquit\nframes 3\n")
    code, out = run_prompt(monkeypatch, capsys, [f"run {path}", "show"])
    assert code == 0
    assert out.rstrip().endswith("spektro> quit\nAvslutar.")
    assert "frames: 3" not in out


def test_comments_and_pasted_prompt(tmp_path):
    """KOM-03, KOD-11, UX-26: # är en kommentar i prompten, en rad med bara # gör ingenting, spektro> tas bort."""
    state = new_state()
    assert registry.run_command(state, "frames 2  # två bilder") is None
    assert state["settings"]["frames"] == 2
    assert registry.run_command(state, "   # bara en kommentar") is None
    registry.run_command(state, "spektro> frames 3")
    assert state["settings"]["frames"] == 3


def test_wait(monkeypatch, capsys):
    """KOM-07: wait 2 väntar två sekunder (time.sleep fejkad); 0 och 601 ger fel."""
    slept = []
    monkeypatch.setattr(files_cmds.time, "sleep", slept.append)
    state = new_state()
    registry.run_command(state, "wait 2")
    assert slept == [2]
    assert capsys.readouterr().out == "väntar 2 s\n"
    assert error_text(state, "wait 0") == "input.invalid_argument: SEKUNDER ska vara minst 1"
    assert error_text(state, "wait 601") == "input.invalid_argument: SEKUNDER ska vara högst 600"


@pytest.mark.parametrize(("name", "peak"), [
    ("direkt.txt", "Topp 200 vid pixel 12 (3 bilder)"),
    ("kalibrera.txt", "Topp 200 vid våglängd (nm) 520 (1 bild)"),
    ("transmission.txt", "Topp 0.5 vid pixel 12 (1 bild)"),
])
def test_exempel_files_run(name, peak, monkeypatch, tmp_path, capsys):
    """DOK-18: exempelfilerna går igenom på testbilderna utan fel och ger toppen (i en kopia, så data/ hamnar i tmp)."""
    shutil.copytree(ROT / "tests", tmp_path / "tests")
    shutil.copytree(ROT / "exempel", tmp_path / "exempel")
    monkeypatch.chdir(tmp_path)
    assert len(files_cmds.command_lines(f"exempel/{name}")) <= 10
    registry.run_command(new_state(), f"run exempel/{name}")
    assert peak in capsys.readouterr().out.splitlines()
