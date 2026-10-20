"""1.2.0 exposure, gain och auto: valet i state, satt varje gång kameran öppnas, i show och settings.json; step varnar."""

import json

import cv2
import pytest
from test_elias import FakeCamera, line_image, new_state

from spectrometer import registry, source


class ControlCamera(FakeCamera):
    """FakeCamera med reglage: set sparar värdet så att get läser det, utom för reglagen i refused."""

    def __init__(self, frames, backend="V4L2", refused=()):
        super().__init__(frames)
        self.backend = backend
        self.refused = refused
        self.calls = []

    def set(self, prop, value):
        self.calls.append((prop, value))
        if prop in self.refused:
            return False
        self.props[prop] = value
        return True

    def release(self):
        pass  # samma låtsaskamera öppnas igen vid nästa kommando

    def getBackendName(self):
        return self.backend


def use_control_camera(monkeypatch, cam):
    """Byter cv2.VideoCapture mot kameran cam."""
    monkeypatch.setattr(source.cv2, "VideoCapture", lambda index, backend: cam)
    return cam


def test_controls_with_a_file_are_kept(tmp_path, capsys):
    """Med en bildfil som källa sparas valet; show skriver det sist och settings.json har det före coefficients."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    for line in (f"source file {path.as_posix()}", "auto off", "exposure -6", "gain 0", "show", "step",
                 f"save {(tmp_path / 'data').as_posix()}"):
        registry.run_command(state, line)
    lines = capsys.readouterr().out.splitlines()
    assert lines[1:4] == ["auto off (sätts när kameran öppnas)", "exposure -6 (sätts när kameran öppnas)",
                          "gain 0 (sätts när kameran öppnas)"]
    assert lines[lines.index("mätning: nej") + 1] == "kamera: auto off, exposure -6, gain 0"
    settings = json.loads((next((tmp_path / "data").iterdir()) / "settings.json").read_text(encoding="utf-8"))
    assert settings["controls"] == {"auto": False, "exposure": -6.0, "gain": 0.0}
    assert list(settings).index("controls") < list(settings).index("coefficients")


def test_camera_gets_the_controls_every_time(monkeypatch, capsys):
    """auto först och sedan exposure, vid varje öppning; drivrutinens svar skrivs (V4L2: manuell är 1)."""
    cam = use_control_camera(monkeypatch, ControlCamera([line_image()] * 2))
    state = new_state()
    for line in ("source camera 0", "auto off", "exposure 150"):
        registry.run_command(state, line)
    assert capsys.readouterr().out.splitlines()[-4:] == [
        "Öppnar kameran ...", "auto off (drivrutinen säger auto off)",
        "Öppnar kameran ...", "exposure 150 (drivrutinen säger exposure 150)",
    ]
    cam.calls.clear()
    registry.run_command(state, "step")
    assert cam.calls == [(cv2.CAP_PROP_AUTO_EXPOSURE, 1.0), (cv2.CAP_PROP_EXPOSURE, 150.0)]


def test_step_warns_when_the_driver_says_auto(monkeypatch, capsys):
    """KRV-03: säger drivrutinen auto-exponering (V4L2: 3) varnar step; efter auto off gör den det inte."""
    cam = use_control_camera(monkeypatch, ControlCamera([line_image()] * 2))
    cam.props[cv2.CAP_PROP_AUTO_EXPOSURE] = 3.0
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "step")
    assert "Varning: auto-exponering är på" in capsys.readouterr().out
    registry.run_command(state, "auto off")
    registry.run_command(state, "step")
    assert "auto-exponering" not in capsys.readouterr().out


def test_refused_control_warns(monkeypatch, capsys):
    """En drivrutin som säger nej ger en varning; DirectShow får auto som 0,25 (manuell)."""
    cam = use_control_camera(monkeypatch, ControlCamera([], backend="DSHOW", refused=(cv2.CAP_PROP_GAIN,)))
    state = new_state()
    for line in ("source camera 0", "auto off", "gain 4"):
        registry.run_command(state, line)
    assert capsys.readouterr().out.splitlines()[-2:] == [
        "Varning: kameran tog inte emot gain; info visar vad drivrutinen har", "gain 4 (drivrutinen säger gain 0)",
    ]
    assert (cv2.CAP_PROP_AUTO_EXPOSURE, 0.25) in cam.calls


def test_bad_words_and_undo():
    """Fel ord ger input.invalid_argument; undo lägger tillbaka det gamla valet."""
    state = new_state()
    registry.run_command(state, "source file bild.png")  # filen behöver inte finnas: exposure öppnar ingen fil
    for line, text in (("exposure x", "N ska vara ett tal, fick x"), ("exposure inf", "N ska vara ett ändligt tal"),
                       ("auto av", "auto tar on eller off"), ("gain", "gain: N saknas")):
        with pytest.raises(ValueError, match=text):
            registry.run_command(state, line)
    registry.run_line(state, "exposure 5")
    registry.run_line(state, "undo")
    assert state["controls"]["exposure"] is None
