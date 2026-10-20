"""1.0.27 Mörkret: löpande summa, varningen i ROI:n, frågan vid kameran och starkt negativa värden."""

import io
import sys

import cv2
import numpy as np
from test_elias import FakeCamera, line_image, new_state

from spectrometer import registry, source


class Tty(io.StringIO):
    """Låtsasterminal: isatty svarar True, så att programmet frågar som vid riggen."""

    def isatty(self):
        return True


def cameras(monkeypatch, frames):
    """Varje öppning av kameran ger en ny låtsaskamera som läser vidare i samma lista med bilder."""
    feed = list(frames)

    def fake_capture(index, backend):
        cam = FakeCamera([])
        cam.frames = feed  # samma lista: nästa öppning fortsätter där den förra slutade
        return cam

    monkeypatch.setattr(source.cv2, "VideoCapture", fake_capture)


def terminal(monkeypatch, answers):
    """Stdin blir en terminal och input svarar med answers i tur och ordning. Ger listan med frågorna."""
    asked = []
    feed = iter(answers)

    def fake_input(prompt):
        asked.append(prompt)
        return next(feed)

    monkeypatch.setattr(sys, "stdin", Tty())
    monkeypatch.setattr("builtins.input", fake_input)
    return asked


def test_dark_running_mean(monkeypatch):
    """PRO-01: mörkret är medlet av bilderna (90, 100 och 110 ger 100), räknat med löpande summa."""
    cameras(monkeypatch, [line_image(value=v) for v in (90, 100, 110)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 3")
    assert state["dark"].dtype == np.float64
    assert state["dark"].shape == (10, 20, 3)
    assert np.all(state["dark"][:, 12] == 100)
    assert np.all(state["dark"][:, :12] == 0)


def test_dark_warning_looks_in_roi(monkeypatch, capsys):
    """PRO-04: ljus i ROI:n ger varningen, ströljus bara utanför ROI:n ger den inte."""
    image = line_image(value=200)
    image[:, 2] = 250  # ljus utanför ROI:n höjer hela bildens medel
    leak = line_image(value=150)  # ljusvägen inte blockerad: bandet syns i mörkret
    stray = np.zeros((10, 20, 3), dtype="uint8")
    stray[:, 2] = 250  # blockerad ljusväg, men ströljus utanför ROI:n
    cameras(monkeypatch, [image, leak, image, stray])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "roi 12 0 1 10")
    registry.run_command(state, "step")
    registry.run_command(state, "dark 1")
    assert "Varning: mörkret liknar bilden. Var ljusvägen blockerad?" in capsys.readouterr().out
    registry.run_command(state, "step")
    registry.run_command(state, "dark 1")
    assert "Var ljusvägen blockerad?" not in capsys.readouterr().out


def test_dark_asks_on_camera_in_terminal(monkeypatch, capsys):
    """UX-20: på kamera i en terminal frågar dark först; avbryt behåller det gamla mörkret."""
    cameras(monkeypatch, [line_image(value=0)])
    asked = terminal(monkeypatch, ["avbryt", ""])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 1")
    assert state["dark"] is None
    assert "Avbrutet." in capsys.readouterr().out
    registry.run_command(state, "dark 1")
    assert state["dark"] is not None
    assert asked == ["Blockera ljusvägen och tryck Enter (skriv avbryt för att hoppa över): "] * 2


def test_reference_asks_on_camera_in_terminal(monkeypatch):
    """UX-20: reference på kamera i en terminal ber om att provet tas bort."""
    cameras(monkeypatch, [line_image(value=0), line_image()])
    asked = terminal(monkeypatch, ["", ""])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 1")
    registry.run_command(state, "reference 1")
    assert asked[1] == "Ta bort provet och tryck Enter: "
    assert state["reference"] is not None


def test_no_question_for_file(monkeypatch, tmp_path):
    """UX-20: en bildfil ger ingen fråga, inte ens i en terminal (pipad indata frågar aldrig, se facit)."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    asked = terminal(monkeypatch, [])
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "dark 1")
    assert asked == []
    assert state["dark"] is not None


def test_negative_after_dark_warns(monkeypatch, capsys):
    """LOG-17: ett mörker som är ljusare än bilden ger starkt negativa värden och en varning efter step."""
    cameras(monkeypatch, [line_image(value=200), line_image(value=0)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "dark 1")
    registry.run_command(state, "step")
    out = capsys.readouterr().out
    assert "Varning: 1 position under -5 counts efter mörkeravdrag. Mörkret passar inte" in out
