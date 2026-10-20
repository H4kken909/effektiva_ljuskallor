"""1.2.3 fwhm: toppar, linjebredd vid halva höjden och area i senaste mätningen (analysis/peaks.py)."""

import cv2
import numpy as np
import pytest
from test_elias import line_image, new_state
from test_kalibrering import spectrum_image, state_with_image

from spectrometer import registry
from spectrometer.analysis import peaks


def test_t07_fwhm_one_nm():
    """T07 (ANA-12): 0, 2, 0 vid 500, 501, 502 nm korsar halva höjden vid 500,5 och 501,5: FWHM 1 nm."""
    x, y = np.array([500.0, 501.0, 502.0]), np.array([0.0, 2.0, 0.0])
    assert peaks.fwhm(x, y, 1) == 1.0


def test_fwhm_on_the_line_image(tmp_path, capsys):
    """En linje på 200 vid pixel 12 och noll bredvid: läge 12, FWHM 1 pixel, area 200 counts·pixel."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    for line in (f"source file {path.as_posix()}", "step", "fwhm"):
        registry.run_command(state, line)
    assert capsys.readouterr().out.splitlines()[-3:] == [
        "topp 1: 12 pixel, höjd 200, FWHM 1 pixel",
        "area: 200 counts·pixel (relativ, inte watt)",
        "FWHM av en smal linje (laser, Hg) är instrumentets upplösning, inte källans bredd.",
    ]


def test_fwhm_gauss_two_peaks(tmp_path, capsys):
    """Två gaussiska toppar med σ = 3 pixlar: FWHM = 2,3548·σ inom 2 %, högst först, och fwhm 1 ger bara den högsta."""
    state = state_with_image(tmp_path, spectrum_image([(100, 200), (300, 100)], sigma=3.0))
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "fwhm")
    rows = [row.replace(",", "").split() for row in capsys.readouterr().out.splitlines() if row.startswith("topp ")]
    assert [round(float(row[2])) for row in rows] == [100, 300]
    assert [float(row[7]) for row in rows] == pytest.approx([2.3548 * 3] * 2, rel=0.02)
    registry.run_command(state, "fwhm 1")
    assert sum(row.startswith("topp ") for row in capsys.readouterr().out.splitlines()) == 1


def test_fwhm_needs_a_measurement():
    with pytest.raises(ValueError, match="Kör step eller load först"):
        registry.run_command(new_state(), "fwhm")
