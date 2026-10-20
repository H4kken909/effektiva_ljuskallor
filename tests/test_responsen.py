"""1.0.28 Responsen: response build med N, varning för svag respons, export till CSV och on i transmission."""

import cv2
import numpy as np
from test_elias import error_text, new_state

from spectrometer import measure, registry


def chain_files(tmp_path):
    """Filerna för kedjan: svart bild, lampa (pixel 10, 11, 12 = 5, 100, 200), punktfil 500–520 nm, känd fördelning."""
    black = np.zeros((10, 20, 3), dtype="uint8")
    lamp = black.copy()
    lamp[:, 10], lamp[:, 11], lamp[:, 12] = 5, 100, 200
    cv2.imwrite(str(tmp_path / "svart.png"), black)
    cv2.imwrite(str(tmp_path / "lampa.png"), lamp)
    (tmp_path / "punkter.csv").write_text("pixel,wavelength_nm,check\n10,500,0\n12,520,0\n", encoding="utf-8")
    (tmp_path / "kand.csv").write_text(
        "wavelength_nm,relative_power_per_nm\n490,1\n500,1\n510,1\n520,2\n530,1\n", encoding="utf-8"
    )
    names = {"svart": "svart.png", "lampa": "lampa.png", "punkter": "punkter.csv", "kand": "kand.csv"}
    return {key: (tmp_path / name).as_posix() for key, name in names.items()}


def calibrated(tmp_path):
    """State med mörker, ROI 10 0 3 2, kanal red och kalibrering, klar för response build. Ger (state, filerna)."""
    paths = chain_files(tmp_path)
    state = new_state()
    for line in (f"source file {paths['svart']}", "dark 1", f"source file {paths['lampa']}", "roi 10 0 3 2",
                 "channel red", f"calibrate {paths['punkter']}"):
        registry.run_command(state, line)
    return state, paths


def test_response_build_takes_n(tmp_path, monkeypatch):
    """KOM-18: response build KNOWNFILE N mäter lampan med N bilder, utan N med CAPTURE_FRAMES."""
    state, paths = calibrated(tmp_path)
    seen = []
    real = measure.measure_direct

    def counting(state, n):
        seen.append(n)
        return real(state, n)

    monkeypatch.setattr(measure, "measure_direct", counting)
    registry.run_command(state, f"response build {paths['kand']} 2")
    registry.run_command(state, f"response build {paths['kand']}")
    assert seen == [2, measure.CAPTURE_FRAMES]
    assert error_text(state, f"response build {paths['kand']} x") == "input.invalid_argument: N ska vara ett heltal, fick x"
    text = error_text(state, "response build a 2 3")
    assert text == "input.invalid_argument: response build tar högst två ord (KNOWNFILE N)"
    assert error_text(state, "response build") == "input.invalid_argument: response: KNOWNFILE saknas"


def test_response_weak_warning(tmp_path, capsys):
    """PRO-31: respons 0.05 vid 500 nm (mellan min_response 0.01 och 0.1) ger varningen om brus."""
    state, paths = calibrated(tmp_path)
    capsys.readouterr()
    registry.run_command(state, f"response build {paths['kand']} 1")
    assert capsys.readouterr().out.splitlines() == [
        "respons: 3 av 3 positioner giltiga",
        "Varning: 1 position har respons under 0.1 (bruset förstärks mer än 10 gånger)",
    ]


def test_response_export(tmp_path, capsys):
    """PRO-27: response export skriver wavelength_nm,response,valid med tom cell där responsen saknas."""
    state, _ = calibrated(tmp_path)
    known = tmp_path / "kand_505.csv"  # börjar vid 505 nm: 500 nm ligger utanför och blir ogiltig
    known.write_text("wavelength_nm,relative_power_per_nm\n505,1\n510,1\n520,2\n530,1\n", encoding="utf-8")
    registry.run_command(state, f"response build {known.as_posix()} 1")
    target = tmp_path / "respons.csv"
    registry.run_command(state, f"response export {target.as_posix()}")
    assert target.read_text(encoding="utf-8").splitlines() == [
        "wavelength_nm,response,valid", "500,,false", "510,1,true", "520,1,true",
    ]
    assert f"respons: sparad i {target.as_posix()}" in capsys.readouterr().out
    text = error_text(new_state(), "response export x.csv")
    assert text == "input.missing_data: ingen respons, kör response build först"


def test_response_on_in_transmission(tmp_path, capsys):
    """PRO-30: response on och show säger att responsen inte används i mode transmission."""
    state, paths = calibrated(tmp_path)
    for line in (f"response build {paths['kand']} 1", "reference 1", "mode transmission"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "response on")
    registry.run_command(state, "show")
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "respons: on (används inte i mode transmission)"
    assert "respons: ja, on (används inte i mode transmission)" in out
    registry.run_command(state, "mode direct")
    registry.run_command(state, "response on")
    assert capsys.readouterr().out.splitlines()[-1] == "respons: on"
