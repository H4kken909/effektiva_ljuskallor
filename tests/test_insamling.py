"""1.0.36 Långa insamlingar: gränsen 1000 bilder, förloppsraden, tiden för långa mätningar och start SEKUNDER."""

import cv2
import numpy as np
from test_elias import error_text, line_image, new_state

from spectrometer import measure, out, plot, registry, source


class FakeCap:
    """Låtsaskamera som alltid ger samma bild."""

    def __init__(self, image):
        self.image = image

    def isOpened(self):
        return True

    def read(self):
        return True, self.image.copy()

    def release(self):
        pass

    def get(self, prop):
        return 0.0


def image_state(tmp_path):
    """State med en linjebild som källa."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    return state


def test_at_most_1000_frames(tmp_path):
    """KOM-39: frames, dark, reference och response build tar högst 1000 bilder; 1000 går."""
    state = image_state(tmp_path)
    assert error_text(state, "frames 1000") is None
    for line in ("frames 1001", "dark 1001", "response build x.csv 1001"):
        assert error_text(state, line) == "input.invalid_argument: N ska vara högst 1000", line
    state["dark"] = np.zeros((10, 20, 3))
    assert error_text(state, "reference 1001") == "input.invalid_argument: N ska vara högst 1000"
    assert state["settings"]["frames"] == 1000


def test_progress_only_above_four_frames(monkeypatch, tmp_path, capsys):
    """UT-17, PRO-39: measure, reference och response build går genom out.progress först över 4 bilder."""
    seen = []

    def spy(items, text):
        seen.append((text, len(items)))
        return items

    monkeypatch.setattr(out, "progress", spy)
    state = image_state(tmp_path)
    registry.run_command(state, "frames 4")
    registry.run_command(state, "step")
    assert seen == []
    registry.run_command(state, "frames 5")
    registry.run_command(state, "step")
    state["dark"] = np.zeros((10, 20, 3))
    registry.run_command(state, "reference 6")
    assert seen == [("mäter", 4), ("mäter", 5)]
    assert "Topp 200 vid pixel 12 (5 bilder)" in capsys.readouterr().out


def test_long_measurement_says_how_long(monkeypatch, tmp_path, capsys):
    """LOG-19: när N gånger tiden för första bilden är över SLOW_SECONDS kommer en rad med tiden före toppen."""
    state = image_state(tmp_path)
    registry.run_command(state, "frames 3")
    capsys.readouterr()
    registry.run_command(state, "step")
    assert capsys.readouterr().out == "Topp 200 vid pixel 12 (3 bilder)\n"
    monkeypatch.setattr(measure, "SLOW_SECONDS", -1)
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines() == [
        "Mäter 3 bilder, ca 1 min. Ctrl+C avbryter.",
        "Topp 200 vid pixel 12 (3 bilder)",
    ]


def test_start_stops_by_itself(monkeypatch, capsys):
    """KOM-42: start SEKUNDER stoppar live efter så lång tid och stänger kameran; 0 och två ord ger fel."""
    cam = FakeCap(line_image())
    released = []
    cam.release = lambda: released.append(True)
    monkeypatch.setattr(source.cv2, "VideoCapture", lambda index, backend: cam)
    monkeypatch.setattr(plot, "open_plot", lambda: {"fig": object()})
    monkeypatch.setattr(plot, "draw", lambda win, x, values, x_label, y_label: None)
    monkeypatch.setattr(plot, "is_open", lambda win: True)
    monkeypatch.setattr(plot, "pause", lambda seconds: None)
    monkeypatch.setattr(plot, "close", lambda win: None)
    state = new_state()
    registry.run_command(state, "start 0.05")
    assert capsys.readouterr().out.splitlines()[-1] == "live stoppad"
    assert released == [True]
    assert state["spectrum"] is not None
    assert error_text(state, "start 0") == "input.invalid_argument: SEKUNDER ska vara ett ändligt tal större än 0"
    assert error_text(state, "start 1 2") == "input.invalid_argument: start tar högst ett ord (SEKUNDER)"
