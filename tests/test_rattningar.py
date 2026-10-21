"""1.2.13 Rättningar ur glappanalysen: bandgap utan kant, calibrate save utan upplösning, fel mapp, mix med roi full
och versionen."""

import json

import numpy as np
from test_bandgap import X, edge_at, transmission_state
from test_blandning import led
from test_elias import error_text, new_state
from test_noggrannhet import calibrated_on_a_line

from spectrometer import __version__, registry
from spectrometer.analysis import bandgap


def test_bandgap_flat_noisy_transmission_has_no_edge():
    """KODFYND 1.2.9: T ≈ 1 med 1 % brus gav förut 2,03 eV. Nu: ingen kant, absorbansen stiger inte 0,1."""
    rng = np.random.default_rng(7)
    flat = 1 + rng.normal(0, 0.01, X.size)
    text = error_text(transmission_state(flat), "bandgap")
    assert text.startswith("input.missing_data: ingen absorptionskant: absorbansen stiger bara ")
    assert text.endswith("minst 0.1 behövs (T ska falla under ca 80 %)")


def test_bandgap_the_synthetic_edge_still_gives_its_value(capsys):
    """Den syntetiska kanten vid 550 nm stiger ca 0,9 i absorbans (T under 0,05 räknas inte) och ger samma värde som förut."""
    absorb = bandgap.absorbance(edge_at(550), edge_at(550) >= bandgap.T_MIN)
    assert bandgap.rise(X, absorb) > 0.5
    registry.run_command(transmission_state(edge_at(550)), "bandgap")
    assert capsys.readouterr().out.splitlines()[0].startswith("bandgap: 2.248 ± ")


def test_calibrate_save_without_resolution_saves_and_warns(tmp_path, capsys):
    """KODFYND 1.2.10: utan mätning efter calibrate sparas filen ändå (resolution_nm null), men med en varning."""
    state, _points = calibrated_on_a_line(tmp_path)
    state["spectrum"] = None
    path = tmp_path / "utan.json"
    capsys.readouterr()
    registry.run_command(state, f"calibrate save {path.as_posix()}")
    rows = capsys.readouterr().out.splitlines()
    assert rows[2] == ("Varning: upplösning okänd, resolution_nm blir null: mät en smal linje med step efter calibrate "
                       "och spara igen med ett nytt namn")
    assert rows[-1] == f"Sparad i {path.as_posix()}"
    assert json.loads(path.read_text(encoding="utf-8"))["resolution_nm"] is None


def test_not_a_measurement_folder(tmp_path):
    """KODFYND 1.2.2, 1.2.4, 1.2.8: load, compare, figure, mix och bandgap på fel mapp ger en Fel-rad, inte [Errno 2]."""
    empty = (tmp_path / "tom").as_posix()
    (tmp_path / "tom").mkdir()
    gone = (tmp_path / "finns_inte").as_posix()
    for line in (f"load {empty}", f"compare {empty}", f"figure {(tmp_path / 'f.png').as_posix()} {empty}",
                 f"mix {empty} {empty} {empty} --sweep", f"bandgap {empty}"):
        assert error_text(new_state(), line) == f"input.invalid_argument: {empty} är ingen mätmapp (spectrum.csv saknas)"
    for line in (f"load {gone}", f"bandgap {gone}"):
        assert error_text(new_state(), line) == f"input.invalid_argument: {gone} finns inte"


def test_mix_roi_full_with_the_same_area_is_no_difference(tmp_path, capsys):
    """KODFYND 1.2.8: roi full sparas som null; med image_size 20 x 10 är det samma yta som roi 0 0 20 10."""
    size = {"image_size": [20, 10]}
    red, green = led(tmp_path, "r", 630, roi=None, **size), led(tmp_path, "g", 530, **size)
    blue = led(tmp_path, "b", 460, **size)
    registry.run_command(new_state(), f"mix {red} {green} {blue} --sweep")
    assert "skiljer sig" not in capsys.readouterr().out
    smaller = led(tmp_path, "b2", 460, roi=[0, 0, 10, 10], **size)
    registry.run_command(new_state(), f"mix {red} {green} {smaller} --sweep")
    assert "Varning: mätningarna skiljer sig i roi; vikterna jämför då olika saker" in capsys.readouterr().out


def test_version_is_not_stuck():
    """__version__ följer utgåvan (stod på 1.0.32 sedan 1.0.32); settings.json och figure skriver den."""
    assert tuple(int(part) for part in __version__.split(".")) >= (1, 2, 13)
