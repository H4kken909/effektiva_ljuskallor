"""1.2.7 Färg: CIE 1931 xy, färgtemperatur (McCamy), V(λ) och kommandot color. Räkningen, inte instrumentet."""

from pathlib import Path

import numpy as np
import pytest
from test_elias import error_text, new_state
from test_responsen import calibrated

from spectrometer import files, registry
from spectrometer.analysis import color

ROT = Path(__file__).resolve().parents[1]
LAM = np.arange(380.0, 781.0)
ALL = np.ones(LAM.size, dtype=bool)


def chromaticity(values, mask=ALL):
    """x, y för ett spektrum på LAM."""
    return color.xy(*color.xyz(LAM, values, mask))


def test_planck_2856_gives_cie_a():
    """ANA-57 och ANA-40: Planck 2856 K ger x ≈ 0,4476, y ≈ 0,4074 och färgtemperaturen 2856–2860 K."""
    x, y = chromaticity(color.planck(LAM, 2856))
    assert abs(x - 0.4476) < 1e-3 and abs(y - 0.4074) < 1e-3
    assert 2850 < color.cct_mccamy(x, y) < 2865


def test_equal_energy_and_555_nm():
    """ANA-57: likenergispektrum ger x = y = 1/3 inom 1e-3; 555 nm ensam ger ett grönt y över 0,6."""
    x, y = chromaticity(np.ones(LAM.size))
    assert abs(x - 1 / 3) < 1e-3 and abs(y - 1 / 3) < 1e-3
    x, y = chromaticity(np.where(LAM == 555, 1.0, 0.0))
    assert y > 0.6 > x


def test_lampa_a_file():
    """PRO-20: kalibrering/lampa_A.csv har 300–830 nm i steg om 1 nm, 100 vid 560 nm och kvoten 1,776 vid 650/550."""
    nm, power = files.load_known(ROT / "kalibrering" / "lampa_A.csv")
    assert nm[0] == 300 and nm[-1] == 830 and nm.size == 531
    assert power[nm == 560][0] == pytest.approx(100)
    assert power[nm == 650][0] / power[nm == 550][0] == pytest.approx(1.776, abs=1e-3)
    x, y = chromaticity(np.interp(LAM, nm, power))
    assert abs(x - 0.4476) < 1e-3 and abs(y - 0.4074) < 1e-3


def test_coverage_of_the_window():
    """Kamerans fönster 400–700 nm täcker över 95 %; 450–650 nm gör det inte (z̄ ligger i blått)."""
    assert color.coverage(LAM, ALL) == pytest.approx(1.0)
    assert color.coverage(LAM, (LAM >= 400) & (LAM <= 700)) > color.MIN_COVERAGE
    assert color.coverage(LAM, (LAM >= 450) & (LAM <= 650)) < color.MIN_COVERAGE


def measured(values, mask=ALL):
    """State med kalibrering, response on och en mätning på LAM."""
    state = new_state()
    state["coefficients"] = np.array([380.0, 1.0])
    state["use_response"] = True
    state["spectrum"] = {"x": LAM, "values": values, "mask": mask}
    return state


def test_color_command_on_a_glow_lamp(capsys):
    """KRV-22 och KRV-24: color skriver xy, färgtemperatur, avstånden till SUB1:s vitpunkter och relativ ljusstyrka."""
    planck = color.planck(LAM, 2856)
    registry.run_command(measured(planck / planck.max()), "color")
    assert capsys.readouterr().out.splitlines() == [
        "färg: x 0.4475  y 0.4075  (CIE 1931 2°)",
        "färgtemperatur: 2858 K (McCamy; avstånd till svartkroppskurvan 0.0001 i uv)",
        "avstånd till varmt vitt (0.45, 0.41): 0.0035",
        "avstånd till kallt vitt (0.31, 0.32): 0.1630",
        "täckning: 100.0 % av x̄, ȳ och z̄ inom det mätta intervallet",
        "ljusstyrka (V(λ)-vägd, relativ): 44.67, jämför bara mätningar med samma inställningar",
    ]


def test_color_warns_for_a_narrow_window_and_a_green_led(capsys):
    """Smal mätning ger varningen om täckningen; en grön LED ger ingen färgtemperatur om McCamy hamnar utanför."""
    window = (LAM >= 450) & (LAM <= 650)
    registry.run_command(measured(np.where(window, 1.0, 0.0), window), "color")
    assert "Varning: en del av spektrumet saknas (täckning under 95 %), x och y kan vara fel" in capsys.readouterr().out
    registry.run_command(measured(np.exp(-0.5 * ((LAM - 525) / 12) ** 2)), "color")
    assert capsys.readouterr().out.splitlines()[1].startswith("färgtemperatur: ingen")


def test_color_needs_measurement_calibration_and_response():
    state = new_state()
    assert error_text(state, "color") == "input.missing_data: Ingen mätning än. Kör step först."
    state = measured(np.ones(LAM.size))
    state["use_response"] = False
    assert error_text(state, "color") == (
        "input.missing_data: color kräver response on i mode direct (annars är det kamerans färg)"
    )
    state["coefficients"] = None
    assert error_text(state, "color") == "input.missing_data: ingen kalibrering, kör calibrate först"
    assert error_text(measured(np.ones(LAM.size)), "color x") == "input.invalid_argument: color: för många ord, väntade 0"


def test_color_after_the_real_chain(tmp_path, capsys):
    """Hela kedjan på testbilderna: mörker, kalibrering, respons på, step och color."""
    state, paths = calibrated(tmp_path)
    for line in (f"response build {paths['kand']} 1", "response on", "step"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "color")
    rows = capsys.readouterr().out.splitlines()
    assert rows[0].startswith("färg: x ")
    assert "Varning: en del av spektrumet saknas" in "\n".join(rows)  # bara 500–520 nm är mätt
