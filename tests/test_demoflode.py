"""1.2.11 Demoflödet: run exempel/demo/mät.txt med låtsaskamera, guide med bockar, pause och help limits mot README."""

from pathlib import Path

import numpy as np
from test_demo import gradient, make_rig_files
from test_elias import FakeCamera, error_text, new_state

from spectrometer import registry, source
from spectrometer.commands import demo_cmds

ROT = Path(__file__).resolve().parents[1]


def cameras(monkeypatch, frames):
    """Låtsaskamera som öppnas på nytt i varje kommando; bilderna tas ur samma lista, i ordning."""
    feed = list(frames)

    def open_camera(index, backend):
        camera = FakeCamera([])
        camera.frames = feed  # samma lista: nästa öppning fortsätter där den förra slutade
        return camera

    monkeypatch.setattr(source.cv2, "VideoCapture", open_camera)


def test_guide_on_a_new_state(capsys):
    """KRV-35: inget gjort utom källan; nästa steg är ROI:n."""
    registry.run_command(new_state(), "guide")
    assert capsys.readouterr().out.splitlines() == [
        "[x] källa        kamera 0 (byt med source camera N eller source file BILD)",
        "[ ] ROI          roi X Y W H (roi auto föreslår)",
        "[ ] mörker       dark (blockera ljusvägen)",
        "[ ] kalibrering  calibrate PUNKTFIL.csv",
        "[ ] respons      response build KÄND.csv och response on",
        "[ ] mätning      step",
        "[ ] sparad       save",
        "Nästa: roi X Y W H (roi auto föreslår)",
    ]


def test_demo_file_runs_the_whole_measurement(monkeypatch, tmp_path, capsys):
    """KRV-34: exempel/demo/mät.txt med låtsaskamera: mörker, kalibrering, respons, step, save, color och guide i ordning."""
    make_rig_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    dark = np.full((10, 20, 3), 2, dtype="uint8")
    cameras(monkeypatch, [dark] * 16 + [gradient(60, 160)] * 20)
    state = new_state()
    registry.run_command(state, "roi 0 0 20 10")
    registry.run_command(state, f"run {(ROT / 'exempel' / 'demo' / 'mät.txt').as_posix()}")
    out = capsys.readouterr().out
    for text in ("mörker: 16 bilder", "respons: 20 av 20 positioner giltiga", "Sparad i data/", "färg: x ",
                 "Sätt lysdioden eller lampan som ska mätas framför spalten", "[x] sparad",
                 "Sparad: data/figur.png och data/figur.txt (villkoren till bildtexten)"):
        assert text in out, text
    assert out.splitlines()[-1] == "Allt gjort. Nästa mätning: step och save; color för färgen."
    assert len([p for p in (tmp_path / "data").iterdir() if p.is_dir()]) == 1  # 1.2.16: plus figur.png och .txt
    assert (tmp_path / "data" / "figur.png").is_file()


def test_pause_needs_text():
    assert error_text(new_state(), "pause") == "input.invalid_argument: pause: TEXT saknas"


def test_help_limits_matches_readme(capsys):
    """KRV-36: help limits skriver LIMITS, och varje rad står i README under Begränsningar."""
    registry.run_command(new_state(), "help limits")
    assert capsys.readouterr().out.splitlines() == list(demo_cmds.LIMITS)
    readme = (ROT / "README.md").read_text(encoding="utf-8")
    for line in demo_cmds.LIMITS:
        assert f"- {line}" in readme, line
