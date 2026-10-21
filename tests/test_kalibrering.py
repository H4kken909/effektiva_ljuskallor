"""Kalibreringens tester: toppar och punktfiler med syntetiska bilder som byggs här (ingen binär fil i repot)."""

import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

from spectrometer import files, peaks, registry, session


def spectrum_image(lines, width=640, height=8, sigma=1.5, noise=0.0, seed=1):
    """En bild (height, width, 3) uint8 med gaussiska toppar längs x; lines är (pixel, höjd) i hela bilden."""
    columns = np.arange(width, dtype=np.float64)
    row = np.zeros(width)
    for pixel, top in lines:
        row += top * np.exp(-0.5 * ((columns - pixel) / sigma) ** 2)
    table = row + np.random.default_rng(seed).normal(0, noise, (height, width))
    gray = np.clip(np.round(table), 0, 255).astype("uint8")
    return np.dstack([gray, gray, gray])


def state_with_image(tmp_path, image):
    """En ny state med bilden som källa (bildfil i tmp_path)."""
    path = tmp_path / "spektrum.png"
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f"source file {path.as_posix()}")
    return state


def peak_rows(text):
    """Raderna som börjar med topp, som listor av ord."""
    return [row.split() for row in text.splitlines() if row.startswith("topp ")]


def test_find_peaks_plateau_mask_and_distance():
    values = np.array([0, 5, 1, 0, 9, 9, 9, 0, 3, 4, 0, 8, 0], dtype=np.float64)
    mask = np.ones(values.size, dtype=bool)
    assert peaks.find_peaks(values, mask, 2, 1) == [5, 11, 1, 9]  # platån 4-6 ger mitten, 5
    assert peaks.find_peaks(values, mask, 6, 1) == [5, 11]
    assert peaks.find_peaks(values, mask, 2, 3) == [5, 11, 1]  # 9 ligger 2 från 11 och slås ihop
    mask[11] = False
    assert peaks.find_peaks(values, mask, 2, 1) == [5, 1, 9]


def test_refine_peak_subpixel_and_plateau():
    k = np.arange(20, dtype=np.float64)
    values = np.exp(-0.5 * ((k - 10.3) / 1.5) ** 2)
    assert abs(peaks.refine_peak(values, 10) - 10.3) < 0.05
    assert peaks.refine_peak(np.array([0, 9, 9, 9, 0], dtype=np.float64), 2) == 2.0
    assert peaks.refine_peak(values, 0) == 0.0


def test_toppar_pixels_in_whole_image(tmp_path, capsys):
    state = state_with_image(tmp_path, spectrum_image([(100.4, 200), (250, 120), (400.7, 60), (500, 10)]))
    registry.run_command(state, "roi 50 0 500 8")
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "toppar")
    rows = peak_rows(capsys.readouterr().out)
    assert [row[:3] for row in rows] == [["topp", "1:", "pixel"], ["topp", "2:", "pixel"], ["topp", "3:", "pixel"]]
    np.testing.assert_allclose([float(row[3]) for row in rows], [100.4, 250, 400.7], atol=0.15)
    assert rows[0][4:] == ["värde", "193"]  # pixel 100: 200 · exp(-0.5 · (0.4 / 1.5)²) avrundat
    registry.run_command(state, "toppar 2")
    rows = peak_rows(capsys.readouterr().out)
    np.testing.assert_allclose([float(row[3]) for row in rows], [100.4, 250], atol=0.15)


def test_toppar_without_measurement_and_bad_n(tmp_path):
    state = state_with_image(tmp_path, spectrum_image([(100, 200)]))
    with pytest.raises(ValueError, match="^input.missing_data: Ingen mätning än. Kör step först.$"):
        registry.run_command(state, "toppar")
    registry.run_command(state, "step")
    with pytest.raises(ValueError, match="N ska vara minst 1"):
        registry.run_command(state, "toppar 0")


def test_toppar_flat_spectrum(tmp_path, capsys):
    state = state_with_image(tmp_path, np.full((8, 40, 3), 50, dtype="uint8"))
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "toppar")
    assert capsys.readouterr().out == "inga toppar över 10 % av det högsta värdet\n"


def test_toppar_after_calibrate_nm_and_outside_fit(tmp_path, capsys):
    state = state_with_image(tmp_path, spectrum_image([(100.4, 200), (250, 120), (400.7, 60)]))
    points = tmp_path / "p.csv"
    points.write_text("pixel,wavelength_nm,check\n100,500,0\n300,700,0\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {points.as_posix()}")
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "toppar")
    lines = [row for row in capsys.readouterr().out.splitlines() if row.startswith("topp ")]
    assert len(lines) == 3
    assert "500.4 nm" in lines[0] and "utanför" not in lines[0]
    assert lines[2].endswith("800.7 nm  (utanför anpassat intervall)")


def test_toppar_descending_calibration_keeps_pixels(tmp_path, capsys):
    state = state_with_image(tmp_path, spectrum_image([(100.4, 200), (250, 120)]))
    points = tmp_path / "ned.csv"
    points.write_text("pixel,wavelength_nm,check\n100,700,0\n300,500,0\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {points.as_posix()}")
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "toppar")
    rows = peak_rows(capsys.readouterr().out)
    np.testing.assert_allclose([float(row[3]) for row in rows], [100.4, 250], atol=0.15)
    assert rows[0][6:8] == ["699.6", "nm"]


ROT = Path(__file__).resolve().parents[1]
HG = [404.656, 435.833, 546.074, 576.960, 579.066]
LINJER = (ROT / "exempel" / "kalibrering" / "hg_linjer.csv").as_posix()


def hg_image(nm_per_pixel=0.4, sigma=1.5, noise=2.0):
    """Hg-lampans fem linjer som gaussiska toppar med brus, pixel = (nm - 380) / nm_per_pixel. Ger (bild, pixlar)."""
    pixels = [(nm - 380) / nm_per_pixel for nm in HG]
    image = spectrum_image(list(zip(pixels, [120, 200, 230, 90, 100])), 640, 480, sigma, noise)
    return image, pixels


def point_rows(text):
    """Raderna i förslaget som börjar med en siffra, delade vid komma."""
    return [row.split(",") for row in text.splitlines() if row[:1].isdigit()]


def test_match_peaks_all_lines_and_merged_doublet():
    chosen, rms, next_rms = peaks.match_peaks([61.6, 139.6, 415.2, 492.4, 497.7], HG)
    np.testing.assert_allclose(chosen, HG)
    assert rms < 0.1 and next_rms == float("inf")
    merged = [24.656, 55.833, 166.074, 198.0]  # 1 nm per pixel, 577 och 579 som en topp vid 578
    chosen, rms, next_rms = peaks.match_peaks(merged, HG)
    np.testing.assert_allclose(chosen[:3], HG[:3])
    assert chosen[3] in HG[3:]
    assert rms < 1 and next_rms < 2  # båda dubblettlinjerna passar nästan lika bra: därför varningen


def test_toppar_linjefil_proposes_rows(tmp_path, capsys):
    image, pixels = hg_image()
    state = state_with_image(tmp_path, image)
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, f"toppar {LINJER}")
    text = capsys.readouterr().out
    rows = point_rows(text)
    np.testing.assert_allclose([float(row[0]) for row in rows], pixels, atol=0.2)
    assert [row[1] for row in rows] == ["404.656", "435.833", "546.074", "576.96", "579.066"]
    assert [row[2] for row in rows] == ["0", "1", "0", "0", "0"]
    assert "Varning" not in text
    assert state["coefficients"] is None  # förslaget kalibrerar inte


def test_toppar_merged_doublet_warns(tmp_path, capsys):
    image, _pixels = hg_image(nm_per_pixel=1.0, sigma=2.5)
    state = state_with_image(tmp_path, image)
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, f"toppar {LINJER}")
    text = capsys.readouterr().out
    assert [row[1] for row in point_rows(text)][:3] == ["404.656", "435.833", "546.074"]
    assert "Varning: 4 toppar men 5 linjer." in text


def test_toppar_writes_point_file_once(tmp_path):
    image, _pixels = hg_image()
    state = state_with_image(tmp_path, image)
    registry.run_command(state, "step")
    target = (tmp_path / "punkter.csv").as_posix()
    registry.run_command(state, f"toppar {LINJER} {target}")
    _pixels, _nm, is_check = files.load_points(target)
    assert list(is_check) == [False, True, False, False, False]
    with pytest.raises(ValueError, match="punkter.csv finns redan"):
        registry.run_command(state, f"toppar {LINJER} {target}")
    registry.run_command(state, f"calibrate {target}")
    np.testing.assert_allclose(state["coefficients"], [380, 0.4], atol=0.3, rtol=0.005)


def test_mall_refused_until_filled():
    state = session.new_state(session.DEFAULTS)
    with pytest.raises(ValueError, match="samma pixel står två gånger"):
        registry.run_command(state, f"calibrate {(ROT / 'exempel' / 'kalibrering' / 'punkter_MALL.csv').as_posix()}")
    np.testing.assert_allclose(files.load_lines(LINJER), HG)


def test_exempel_files_find_then_fit(tmp_path, monkeypatch, capsys):
    """Kommandofilerna i exempel/ med en testbild i stället för kameran: hitta, skriv punktfilen, anpassa."""
    image, _pixels = hg_image()
    cv2.imwrite(str(tmp_path / "hg.png"), image)
    (tmp_path / "exempel" / "kalibrering").mkdir(parents=True)  # samma sökväg som kommandofilerna använder
    shutil.copy(LINJER, tmp_path / "exempel" / "kalibrering")
    monkeypatch.chdir(tmp_path)
    state = session.new_state(session.DEFAULTS)

    def run(name):
        for line in (ROT / "exempel" / name).read_text(encoding="utf-8").splitlines():
            registry.run_command(state, line.replace("source camera 0", "source file hg.png"))

    run("kalibrera_1_hitta.txt")
    assert "förslag: 5 toppar mot 5 linjer" in capsys.readouterr().out
    registry.run_command(state, "toppar exempel/kalibrering/hg_linjer.csv exempel/kalibrering/punkter.csv")
    run("kalibrera_2_anpassa.txt")
    text = capsys.readouterr().out
    assert "546.1 nm" in text
    assert "Sparad i data/" in text


def calibrate_text(state, tmp_path, rows, words="", name="p.csv"):
    """Skriver punktfilen (rader utan rubrik), kör calibrate med orden efter sökvägen och ger utskriften."""
    points = tmp_path / name
    points.write_text("pixel,wavelength_nm,check\n" + "\n".join(rows) + "\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {points.as_posix()} {words}".strip())
    return points


def test_calibrate_units_and_margin(tmp_path, capsys):
    state = session.new_state(session.DEFAULTS)
    calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"])
    text = capsys.readouterr().out
    assert "a0: 400 nm\na1: 1 nm/pixel\n" in text
    assert "giltigt: pixel 0 till 300" in text  # MARGIN 1 som förut
    calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"], "1 0.25", "q.csv")
    assert "giltigt: pixel 75 till 225" in capsys.readouterr().out
    assert state["pixel_range"] == (75, 225)
    for words, message in (("1 x", "MARGIN ska vara ett tal, fick x"), ("1 -1", "MARGIN ska vara ett tal minst 0"),
                           ("1 1 1", "calibrate tar högst tre ord")):
        with pytest.raises(ValueError, match=message):
            calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"], words, "r.csv")
    assert state["pixel_range"] == (75, 225)  # den gamla står kvar


def test_calibrate_warns_for_deviating_fit_point(tmp_path, capsys):
    state = session.new_state(session.DEFAULTS)
    rows = ["100,500,0", "125,525,0", "150,560,0", "175,575,0", "200,600,0"]  # 150 borde vara 550
    calibrate_text(state, tmp_path, rows)
    warnings = [row for row in capsys.readouterr().out.splitlines() if row.startswith("Varning: residualen")]
    assert "Varning: residualen 8 nm vid pixel 150 är större än steget 1 nm. Hör pixeln till rätt linje?" in warnings
    calibrate_text(state, tmp_path, ["100,500,0", "150,550,0", "200,600,0"], "", "bra.csv")
    assert "Varning" not in capsys.readouterr().out


def test_calibrate_degree2_turning_point(tmp_path, capsys):
    state = session.new_state(session.DEFAULTS)
    rows = ["0,400,0", "100,500,0", "200,550,0"]  # parabeln vänder vid pixel 250
    with pytest.raises(ValueError, match="inte monoton mellan pixel 0 och 400; grad 2 vänder vid pixel 250; prova"):
        calibrate_text(state, tmp_path, rows, "2")
    assert state["coefficients"] is None
    calibrate_text(state, tmp_path, rows, "2 0.2", "q.csv")
    text = capsys.readouterr().out
    assert "a2: -0.0025 nm/pixel^2\n" in text
    assert "giltigt: pixel 0 till 240\ngrad 2 vänder vid pixel 250, utanför giltigt intervall\n" in text


def test_step_refuses_axis_that_turns_in_roi(tmp_path):
    state = state_with_image(tmp_path, spectrum_image([(100, 200)], width=320))
    calibrate_text(state, tmp_path, ["0,400,0", "100,500,0", "200,550,0"], "2 0.2")  # giltigt 0 till 240
    registry.run_command(state, "roi 0 0 300 8")  # förbi vändpunkten vid 250
    with pytest.raises(ValueError, match="x-axeln är inte monoton i ROI:n"):
        registry.run_command(state, "step")
    registry.run_command(state, "roi 0 0 240 8")
    registry.run_command(state, "step")
    assert np.all(np.diff(state["spectrum"]["x"]) > 0)


def test_descending_calibration_flips_together(tmp_path, capsys):
    """LOG-27: högre pixel ger lägre nm; x stiger efter vändningen och values och mask följer med."""
    state = state_with_image(tmp_path, spectrum_image([(175, 100), (195, 200)], width=220, sigma=1.0))
    calibrate_text(state, tmp_path, ["180,400,0", "190,390,0"])  # giltigt: pixel 170 till 200
    registry.run_command(state, "roi 160 0 50 8")  # pixel 160 till 209, delvis utanför
    capsys.readouterr()
    registry.run_command(state, "step")
    assert "Topp 200 vid våglängd (nm) 385 (1 bild)" in capsys.readouterr().out
    spectrum = state["spectrum"]
    assert np.all(np.diff(spectrum["x"]) > 0)
    np.testing.assert_allclose(spectrum["x"][[0, -1]], [371, 420])  # pixel 209 först, pixel 160 sist
    assert np.count_nonzero(spectrum["mask"]) == 31  # pixel 170 till 200
    assert not spectrum["mask"][0] and not spectrum["mask"][-1]
    np.testing.assert_allclose(spectrum["values"][209 - 175], 100)  # pixel 175 på plats 34 efter vändningen


def test_save_keeps_calibration_and_loads_it_again(tmp_path, capsys):
    state = state_with_image(tmp_path, spectrum_image([(100, 200)], width=320))
    points = calibrate_text(state, tmp_path, ["100,500,0", "200,600,0"])
    registry.run_command(state, "step")
    registry.run_command(state, f"save {(tmp_path / 'data').as_posix()}")
    folder = next((tmp_path / "data").iterdir())
    saved = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    keys = list(saved)
    for key in ("pixel_range", "image_size", "calibration_points_file"):  # före coefficients: slutet av filen orört
        assert keys.index(key) < keys.index("coefficients")
    assert saved["pixel_range"] == [0.0, 300.0]
    assert saved["image_size"] == [320, 8]
    info = saved["calibration_points_file"]
    assert info["path"] == points.as_posix()
    assert info["sha256"] == hashlib.sha256(points.read_bytes()).hexdigest()[:12]
    assert len(info["time"]) == len("2026-10-20T14:03:12")

    fresh = state_with_image(tmp_path, spectrum_image([(100, 200)], width=320))
    settings = (folder / "settings.json").as_posix()
    capsys.readouterr()
    registry.run_command(fresh, f"calibrate {settings}")
    text = capsys.readouterr().out
    assert text.startswith(f"kalibrering läst ur {settings}\na0: 400 nm\na1: 1 nm/pixel\ngiltigt: pixel 0 till 300\n")
    assert "Varning" not in text
    np.testing.assert_allclose(fresh["coefficients"], state["coefficients"])
    assert fresh["pixel_range"] == (0, 300)
    assert fresh["calibration_points_file"] == info
    registry.run_command(fresh, "step")
    np.testing.assert_allclose(fresh["spectrum"]["x"], state["spectrum"]["x"])


def test_load_warns_and_refuses(tmp_path, capsys):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"axis": "vertical", "coefficients": [400, 1], "pixel_range": [0, 300],
                                    "image_size": [640, 480]}), encoding="utf-8")
    state = state_with_image(tmp_path, spectrum_image([(100, 200)], width=320))
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, f"calibrate {settings.as_posix()}")
    text = capsys.readouterr().out
    assert "Varning: axis är vertical i settings.json men horizontal nu. Pixlarna betyder olika saker." in text
    assert "Varning: bilden var 640x480 pixlar men är 320x8 nu. Pixlarna betyder olika saker." in text
    for content, message in (({"coefficients": [400, 1]}, "saknar pixel_range"),
                             ({"coefficients": None}, "har ingen kalibrering"),
                             ({"coefficients": [1], "pixel_range": [0, 1]}, "fel form")):
        bad = tmp_path / "fel.json"
        bad.write_text(json.dumps(content), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            registry.run_command(state, f"calibrate {bad.as_posix()}")
    assert state["pixel_range"] == (0, 300)  # den lästa står kvar
