"""1.0.29 Referensen: topp och svaga positioner, reference check och varningen först över T = 1,05."""

import cv2
import numpy as np
from test_elias import error_text, line_image, new_state
from test_morkret import cameras

from spectrometer import registry


def test_reference_prints_peak_and_weak(tmp_path, capsys):
    """PRO-35: reference skriver toppen och hur många positioner som ligger under min_reference."""
    black = tmp_path / "svart.png"
    lamp = tmp_path / "lampa.png"
    cv2.imwrite(str(black), np.zeros((10, 20, 3), dtype="uint8"))
    cv2.imwrite(str(lamp), line_image())
    state = new_state()
    for line in (f"source file {black.as_posix()}", "dark 1", f"source file {lamp.as_posix()}"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "reference 1")
    assert capsys.readouterr().out == "Referens: 1 bild, x från 0 till 19, topp 200, 19 av 20 under min_reference\n"


def test_reference_check(monkeypatch, capsys):
    """PRO-36: reference check mäter igen utan att byta och skriver största relativa skillnaden (200 mot 210)."""
    cameras(monkeypatch, [line_image(value=0), line_image(value=200), line_image(value=210)])
    state = new_state()
    for line in ("source camera 0", "dark 1", "reference 1"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "reference check 1")
    assert capsys.readouterr().out == "Öppnar kameran ...\nReferenskontroll: största skillnad 5.0 % vid pixel 12 (1 bild)\n"
    assert round(state["reference"]["values"][12]) == 200  # den sparade referensen är kvar
    assert error_text(state, "reference check 1 2") == "input.invalid_argument: reference check tar högst ett ord (N)"
    assert error_text(new_state(), "reference check") == "input.missing_data: ingen referens, kör reference först"


def test_transmission_warning_above_105(monkeypatch, capsys):
    """LOG-15/16: T = 1.08 ger varningen med antal, högsta värde och plats; T = 1.04 (brus runt 1) ger ingen."""
    frames = [line_image(value=0), line_image(value=100), line_image(value=108), line_image(value=104)]
    cameras(monkeypatch, frames)
    state = new_state()
    for line in ("source camera 0", "dark 1", "reference 1", "mode transmission"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines() == [
        "Öppnar kameran ...",
        "Topp 1.08 vid pixel 12 (1 bild)",
        "Varning: transmission över 105 % på 1 position (högst 1.08 vid pixel 12)",
    ]
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines() == ["Öppnar kameran ...", "Topp 1.04 vid pixel 12 (1 bild)"]
