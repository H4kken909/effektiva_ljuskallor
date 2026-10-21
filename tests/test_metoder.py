"""1.2.15 Metoderna som rev7: FWHM över baslinjen, CCT med Duv och bandgap med två räta linjer."""

import numpy as np
import pytest
from test_bandgap import X, edge_at, transmission_state
from test_elias import error_text, line_image, new_state, use_camera

from spectrometer import registry
from spectrometer.analysis import bandgap, color, peaks

PX = np.arange(200.0)


def gauss(center, sigma, height=100.0):
    return height * np.exp(-0.5 * ((PX - center) / sigma) ** 2)


def test_fwhm_over_a_sloping_background():
    """rev7 L3626: baslinjen mellan baspunkterna dras av; en lutande bakgrund ger samma FWHM som utan (2,3548·σ)."""
    y = 50 + 0.2 * PX + gauss(100, 4)
    assert peaks.fwhm(PX, y, 100) == pytest.approx(2.3548 * 4, rel=0.01)
    assert peaks.fwhm(PX, gauss(100, 4), 100) == pytest.approx(2.3548 * 4, rel=0.01)
    assert peaks.bases(y, 100)[0] == 0


def test_fwhm_invalid_at_the_edge_in_a_doublet_and_after_a_gap():
    """Ogiltig hellre än påhittad: toppen vid kanten, två toppar med dalen över halva höjden, en lucka på flanken."""
    width, why = peaks.width(PX, gauss(199, 4), 199)
    assert np.isnan(width) and why == "okänd (kurvan når inte halva höjden)"
    doublet = gauss(100, 4) + gauss(110, 4)  # två lika höga toppar, dalen (92) över halva höjden (52)
    assert np.isnan(peaks.fwhm(PX, doublet, 100)) and np.isnan(peaks.fwhm(PX, doublet, 110))
    plateau = np.array([0, 0, 100, 200, 200, 100, 0, 0.0])
    assert peaks.fwhm(np.arange(8.0), plateau, 4) == 3  # platån (8 bitar) stoppar inte baspunkterna
    gap = gauss(100, 4)
    gap[102] = np.nan
    assert peaks.width(PX, gap, 100)[1] == "okänd (kurvan når inte halva höjden)"
    resolved = gauss(100, 3) + gauss(130, 3)
    assert peaks.fwhm(PX, resolved, 100) == pytest.approx(2.3548 * 3, rel=0.01)


def test_fwhm_command_says_saturated(monkeypatch, capsys):
    """rev7: mättnad gör bredden ogiltig. En linje på 255 ger FWHM ogiltig, inte ett tal."""
    use_camera(monkeypatch, [line_image(value=255)])
    state = new_state()
    for line in ("source camera 0", "step"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "fwhm 1")
    assert capsys.readouterr().out.splitlines()[0] == "topp 1: 12 pixel, höjd 255, FWHM ogiltig (toppen är mättad)"


def test_cct_of_planck_and_the_e_white_point():
    """CCT som närmaste punkt på Planck-kurvan i uv: 2856 K ger 2856 K och Duv 0; E (1/3, 1/3) ger ca 5455 K, Duv −0,004."""
    cct, duv, limit = color.cct_duv(*color.planck_xy(2856))
    assert cct == pytest.approx(2856, abs=1) and abs(duv) < 1e-5 and not limit
    cct, duv, limit = color.cct_duv(1 / 3, 1 / 3)
    assert cct == pytest.approx(5455, abs=15) and -0.006 < duv < -0.003 and not limit
    for kelvin in (2000, 4000, 6500, 10000):
        assert color.cct_duv(*color.planck_xy(kelvin))[0] == pytest.approx(kelvin, rel=1e-3)


def test_cct_line_rules():
    """rev7 L3683–3685: |Duv| över 0,01 ger ingen CCT; utanför sökområdet ingen heller."""
    assert color.cct_line(*color.planck_xy(2856)).startswith("färgtemperatur: 2856 K, Duv +0.0000 ")
    above = color.cct_line(0.31, 0.36)
    assert above.startswith("färgtemperatur: ingen (Duv +0.0") and above.endswith("CCT saknar mening)")
    assert color.cct_line(0.70, 0.29).startswith("färgtemperatur: ingen")


def test_bandgap_fit_on_the_synthetic_edge(capsys):
    """ANA-48: två räta linjer på kanten vid 550 nm ger brytpunkten inom 0,02 eV från 2,254 eV."""
    registry.run_command(transmission_state(edge_at(550)), "bandgap --anpassa")
    rows = capsys.readouterr().out.splitlines()
    assert rows[0].startswith("bandgap (två räta linjer): ")
    assert abs(float(rows[0].split()[4]) - 1239.84 / 550) < 0.02
    assert rows[2].startswith("ändpunktskontroll: utan första punkten ")
    assert rows[3] == "fönstret 366–766 nm (3.39–1.62 eV): kanten ligger inne"


def hinge_transmission(ec, noise=0.0, seed=1):
    """ANA-56: A = 0,5 + 0,1·(E − ec) + 1,9·max(0, E − ec) (lutningarna 0,1 och 2,0) med brus, som T = 10^−A."""
    E = bandgap.ev(X)
    A = 0.5 + 0.1 * (E - ec) + 1.9 * np.maximum(0, E - ec)
    return 10 ** -(A + np.random.default_rng(seed).normal(0, noise, X.size))


def test_bandgap_fit_finds_a_known_edge_and_refuses_a_straight_line():
    """ANA-56: känd kant 2,0 eV med brus ger 2,0 inom 0,02 eV; en rät linje (ingen brytpunkt) ger ingen kant."""
    lines = bandgap.fit_report(X, hinge_transmission(2.0, noise=0.005), np.ones(X.size, dtype=bool))
    assert abs(float(lines[0].split()[4]) - 2.0) < 0.02
    E = bandgap.ev(X)
    straight = 10 ** -(0.2 + 0.6 * (E - E.min()))
    assert error_text(transmission_state(straight), "bandgap --anpassa").startswith(
        "input.missing_data: ingen absorptionskant: "
    )


def test_bandgap_fit_refuses_too_few_points_and_keeps_the_old_method(capsys):
    """Minst åtta punkter; utan --anpassa är det brantaste lutningen som förut, och fler ord är fel."""
    short = np.full(X.size, np.nan)
    short[100:105] = 0.5
    state = transmission_state(short)
    assert error_text(state, "bandgap --anpassa") == "input.missing_data: för få punkter för två räta linjer (5, minst 8)"
    registry.run_command(transmission_state(edge_at(550)), "bandgap")
    assert capsys.readouterr().out.splitlines()[0] == "bandgap: 2.248 ± 0.003 eV, kanten vid 551.5 nm"
    assert error_text(new_state(), "bandgap a b --anpassa") == "input.invalid_argument: bandgap tar högst ett ord (MAPP)"
