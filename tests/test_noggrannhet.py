"""1.2.10 Noggrannhet: repeat N, linearity och calibrate save med residualer och upplösning. Räkningen, inte riggen."""

import json

import cv2
import numpy as np
from test_elias import error_text, new_state

from spectrometer import registry


def image(columns):
    """En bild 10 x 20 med värdet v i kolumnen c för varje c: v i columns."""
    picture = np.zeros((10, 20, 3), dtype="uint8")
    for column, value in columns.items():
        picture[:, column] = value
    return picture


def folder_source(tmp_path, name, values):
    """En mapp med en bild per värde (linjen i kolumn 12), som källa: en bild per mätning, i ordning."""
    folder = tmp_path / name
    folder.mkdir()
    for k, value in enumerate(values):
        cv2.imwrite(str(folder / f"{k:03d}.png"), image({12: value}))
    state = new_state()
    registry.run_command(state, f"source file {folder.as_posix()}")
    return state


def lines(capsys, state, line):
    """Kör en rad och ger raderna som skrevs."""
    capsys.readouterr()
    registry.run_command(state, line)
    return capsys.readouterr().out.splitlines()


def test_repeat_mean_and_spread(tmp_path, capsys):
    """KRV-31: tre mätningar 190, 200 och 210 ger medel 200 och spridning 10 (ddof=1); CSV per position."""
    state = folder_source(tmp_path, "bilder", (190, 200, 210))
    path = tmp_path / "upprepad.csv"
    assert lines(capsys, state, f"repeat 3 {path.as_posix()}") == [
        "repeat: 3 mätningar med 1 bild var",
        "topp: medel 200, spridning 10 (5.00 %)",
        "toppläge: medel 12 pixel, spridning 0 pixel",
        "area: medel 200, spridning 10 (5.00 %)",
        f"Sparad i {path.as_posix()}",
    ]
    rows = path.read_text(encoding="utf-8").splitlines()
    assert rows[0] == "x_px,mean,stddev,valid" and rows[13] == "12,200,10,true"
    assert state["spectrum"] is None  # repeat mäter i en kopia
    assert error_text(state, f"repeat 3 {path.as_posix()}") == (
        f"input.invalid_argument: {path.as_posix()} finns redan, välj ett annat namn"
    )
    assert error_text(state, "repeat 1") == "input.invalid_argument: N ska vara minst 2"


def test_repeat_default_file_in_output_dir(tmp_path, capsys):
    state = folder_source(tmp_path, "bilder", (200, 200))
    state["settings"]["output_dir"] = (tmp_path / "ut").as_posix()
    assert lines(capsys, state, "repeat 2")[-1].startswith(f"Sparad i {(tmp_path / 'ut').as_posix()}/repeat-")
    assert len(list((tmp_path / "ut").glob("repeat-*.csv"))) == 1


def test_linearity(tmp_path, capsys):
    """KRV-33: proportionell area ger 0 % avvikelse; en böjd serie ger större avvikelse; mättnad varnar."""
    rows = lines(capsys, folder_source(tmp_path, "rak", (50, 100, 150, 200)), "linearity 1 2 3 4")
    assert rows[0] == "rät linje: area = 50·E + 0"
    assert rows[-1] == "största avvikelse från en rät linje: 0.0 %"
    rows = lines(capsys, folder_source(tmp_path, "bojd", (50, 100, 150, 180)), "linearity 1 2 3 4")
    assert rows[-1] == "största avvikelse från en rät linje: 7.4 %"
    rows = lines(capsys, folder_source(tmp_path, "mattad", (85, 170, 255)), "linearity 1 2 3")
    assert "Varning: mättad vid exponering 3: den punkten säger inget om linjäriteten" in rows
    assert error_text(new_state(), "linearity 1 2 2") == (
        "input.invalid_argument: linearity behöver minst tre olika exponeringar (E1 E2 E3)"
    )


def calibrated_on_a_line(tmp_path):
    """State kalibrerad med 10 nm per pixel (tre punkter och en kontrollpunkt) och en mätt linje, FWHM 2 pixlar."""
    picture = tmp_path / "linje.png"
    cv2.imwrite(str(picture), image({11: 100, 12: 200, 13: 100}))
    points = tmp_path / "punkter.csv"
    points.write_text("pixel,wavelength_nm,check\n10,500,0\n12,520,0\n14,540,0\n11,511,1\n", encoding="utf-8")
    state = new_state()
    for line in (f"source file {picture.as_posix()}", f"calibrate {points.as_posix()}", "step"):
        registry.run_command(state, line)
    return state, points


def test_calibrate_save(tmp_path, capsys):
    """KRV-32: residualer, kontrollfel, nm per pixel och resolution_nm (FWHM 2 pixlar = 20 nm) i JSON-filen."""
    state, points = calibrated_on_a_line(tmp_path)
    path = tmp_path / "kalibrering.json"
    assert lines(capsys, state, f"calibrate save {path.as_posix()}") == [
        "kalibrering: rms 0 nm över 3 anpassningspunkter, 10 nm per pixel",
        "kontrollfel: största 1 nm (1 kontrollpunkt)",
        "upplösning: 20 nm (FWHM för högsta toppen i senaste mätningen)",
        f"Sparad i {path.as_posix()}",
    ]
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["resolution_nm"] == 20 and saved["nm_per_pixel"] == 10 and saved["max_check_error_nm"] == 1
    assert [p["error_nm"] for p in saved["points"]] == [0, 0, 0, 1]
    assert saved["points_file"]["path"] == points.as_posix()
    state["spectrum"] = None
    rows = lines(capsys, state, f"calibrate save {(tmp_path / 'utan.json').as_posix()}")
    assert rows[2] == "upplösning: okänd (mät en smal linje med step efter calibrate)"


def test_calibrate_save_refuses(tmp_path, capsys):
    assert error_text(new_state(), "calibrate save k.json") == "input.missing_data: ingen kalibrering, kör calibrate först"
    state, points = calibrated_on_a_line(tmp_path)
    (tmp_path / "finns.json").write_text("{}", encoding="utf-8")
    assert error_text(state, f"calibrate save {(tmp_path / 'finns.json').as_posix()}").endswith("finns redan, välj ett annat namn")
    points.write_text("pixel,wavelength_nm,check\n10,500,0\n14,540,0\n", encoding="utf-8")
    assert error_text(state, f"calibrate save {(tmp_path / 'ny.json').as_posix()}") == (
        "input.invalid_argument: punktfilen har ändrats sedan calibrate, kör calibrate igen"
    )
    registry.run_command(state, f"calibrate {points.as_posix()}")
    rows = lines(capsys, state, f"calibrate save {(tmp_path / 'ny.json').as_posix()}")
    assert rows[1] == "Varning: lika många punkter som koefficienter: residualerna är 0 per definition, lägg till punkter"
