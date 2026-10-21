"""1.2.14 Mätdata till BP5: kolumnen stddev i spectrum.csv, värde ± osäkerhet (RAP-14) och dark save/load."""

import csv

import numpy as np
import pytest
from test_elias import error_text, line_image, new_state, use_camera

from spectrometer import files, out, registry
from spectrometer.analysis import mapp, series


def flank_image(left, right, top=220):
    """En bild 10 x 20 med toppen i kolumn 12 och flankerna left och right i kolumn 11 och 13."""
    image = line_image(value=top)
    image[:, 11], image[:, 13] = left, right
    return image


def saved(tmp_path, monkeypatch, frames, images):
    """step och save med låtsaskameran; ger state och mätmappen."""
    use_camera(monkeypatch, images)
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in ("source camera 0", f"frames {frames}", "step", "save"):
        registry.run_command(state, line)
    return state, next((tmp_path / "data").iterdir())


def test_stddev_column_after_raw_counts(tmp_path, monkeypatch):
    """DAT-02/LOG-14: stddev efter raw_counts, spridningen mellan bilderna (ddof=1); 90 och 110 ger 14.14."""
    _state, folder = saved(tmp_path, monkeypatch, 2, [line_image(value=90), line_image(value=110)])
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["x_px", "value", "valid", "raw_counts", "stddev"]
    assert rows[13][:4] == ["12", "100", "true", "100"]
    assert float(rows[13][4]) == pytest.approx(np.std([90, 110], ddof=1))
    assert rows[1][4] == "0"
    assert "stddev" in (folder / "README.txt").read_text(encoding="utf-8")


def test_stddev_empty_for_one_frame_and_read_back(tmp_path, monkeypatch, capsys):
    """En bild: tom stddev-cell. load och mapp.read läser filer med och utan kolumnen."""
    state, folder = saved(tmp_path, monkeypatch, 1, [line_image()])
    with open(folder / "spectrum.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[13] == ["12", "200", "true", "200", ""]
    loaded = files.load_measurement(folder)
    assert np.all(np.isnan(loaded["stddev"])) and loaded["frames"] == 1
    assert np.all(np.isnan(mapp.read(folder)["columns"]["stddev"]))
    old = tmp_path / "gammal"
    old.mkdir()
    (old / "spectrum.csv").write_text("x_px,value,valid,raw_counts\n0,1.5,true,1.5\n", encoding="utf-8")
    assert "stddev" not in files.load_measurement(old)
    registry.run_command(state, f"load {old.as_posix()}")
    assert capsys.readouterr().out.splitlines()[-1] == "Topp 1.5 vid pixel 0"


@pytest.mark.parametrize(("value", "uncertainty", "unit", "text"), [
    (2.25376, 0.00274, "eV", "2.2538 ± 0.0027 eV"),
    (546.07, 0.4, "nm", "546.1 ± 0.4 nm"),
    (1234.5, 37, "", "1230 ± 40"),
    (0.5, 0.0296, "", "0.500 ± 0.030"),
    (12.34, 9.6, "", "12 ± 10"),
    (7.25, float("nan"), "pixel", "7.25 pixel"),
    (7.25, 0.0, "", "7.25"),
])
def test_pm_rounds_to_the_uncertainty(value, uncertainty, unit, text):
    """RAP-14: 1–2 värdesiffror i osäkerheten (2 när den börjar på 1 eller 2) och värdet till samma decimal."""
    assert out.pm(value, uncertainty, unit) == text


def test_fwhm_with_spread_between_frames(tmp_path, monkeypatch, capsys):
    """Två bilder med flankerna 80/120 och 120/80: FWHM 1,83 pixel och slumpfelet ur spridningen, 0,22 pixel."""
    state, _folder = saved(tmp_path, monkeypatch, 2, [flank_image(80, 120), flank_image(120, 80)])
    capsys.readouterr()
    registry.run_command(state, "fwhm 1")
    assert capsys.readouterr().out.splitlines() == [
        "topp 1: 12 pixel, höjd 220, FWHM 1.83 ± 0.22 pixel",
        "area: 420 counts·pixel (relativ, inte watt)",
        "FWHM av en smal linje (laser, Hg) är instrumentets upplösning, inte källans bredd.",
        "± i FWHM: spridningen mellan 2 bilder (slumpfel); kalibrering och instrument ingår inte",
    ]


def test_series_repeats_give_mean_and_spread(tmp_path, capsys):
    """RAP-14 i series plot: tre mätningar vid 20 mA ger medel ± spridning; en vid 10 mA skrivs som förut."""
    xs, means, spreads, counts = series.repeats([10, 20, 20, 20], [5.0, 9.0, 10.0, 11.0])
    assert xs.tolist() == [10, 20] and means.tolist() == [5, 10] and counts.tolist() == [1, 3]
    assert np.isnan(spreads[0]) and spreads[1] == 1
    folder = tmp_path / "data" / "led"
    folder.mkdir(parents=True)
    for current, area in ((10, 5.0), (20, 9.0), (20, 10.0), (20, 11.0)):
        series.append(folder / "serie.csv", {"current_mA": current, "area": area})
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    registry.run_command(state, f"series plot led {(tmp_path / 'led.png').as_posix()}")
    assert capsys.readouterr().out.splitlines()[:5] == [
        f"serie led: 2 punkter ur {(folder / 'serie.csv').as_posix()}",
        "  10 mA: relativ uteffekt 5, relativ effektivitet 1",
        "  20 mA: relativ uteffekt 10.0 ± 1.0 (3 mätningar), relativ effektivitet 1",
        "  droop: 0 % lägre area/I vid 20 mA än vid max (relativt, inte verkningsgrad)",
        "  ± är spridningen mellan upprepade mätningar vid samma ström; total osäkerhet ej kvantifierad",
    ]


def test_dark_save_and_load(tmp_path, monkeypatch, capsys):
    """PRO-06: dark save skriver .npy (aldrig över), dark load läser tillbaka, prövar formen och varnar för exponeringen."""
    use_camera(monkeypatch, [np.full((10, 20, 3), 3, dtype="uint8")] * 16 + [line_image()])
    state = new_state()
    path = (tmp_path / "mork.npy").as_posix()
    for line in ("source camera 0", "dark", f"dark save {path}"):
        registry.run_command(state, line)
    assert capsys.readouterr().out.splitlines()[-1] == f"mörker: sparat i {path} (20 x 10 pixlar)"
    assert error_text(state, f"dark save {path}") == f"input.invalid_argument: {path} finns redan, dark save skriver inte över"
    other = new_state()
    registry.run_command(other, f"dark load {path}")
    assert capsys.readouterr().out.splitlines() == [
        f"mörker: laddat ur {path}, 20 x 10 pixlar, medel 3",
        "Bildstorleken prövas mot källan vid nästa mätning.",
        "Varning: mörkret gäller bara med samma exponering och gain som när det mättes (filen säger inte vilka)",
    ]
    np.testing.assert_array_equal(other["dark"], state["dark"])
    assert other["dark"].dtype == np.float64 and other["taken"]["dark"] is not None
    other["image"] = np.zeros((20, 40, 3), dtype="uint8")
    assert error_text(other, f"dark load {path}") == (
        "input.invalid_argument: mörkret är 20 x 10 pixlar men bilden ur källan är 40 x 20"
    )
    other["image"] = None
    registry.run_command(other, "roi 10 5 20 5")
    assert error_text(other, f"dark load {path}") == (
        "input.invalid_argument: roi 10 5 20 5 ligger utanför mörkret (20 x 10 pixlar)"
    )


def test_dark_load_refuses_other_files(tmp_path):
    text = tmp_path / "text.npy"
    text.write_text("inget mörker", encoding="utf-8")
    flat = tmp_path / "platt.npy"
    np.save(flat, np.zeros((10, 20)))
    for path in (text, flat):
        assert error_text(new_state(), f"dark load {path.as_posix()}") == (
            f"input.invalid_argument: {path.name} är inget mörker från dark save"
        )
    assert error_text(new_state(), f"dark save {(tmp_path / 'x.npy').as_posix()}") == (
        "input.missing_data: inget mörker, kör dark först"
    )
    gone = (tmp_path / "finns_inte.npy").as_posix()
    assert error_text(new_state(), f"dark load {gone}") == f"input.invalid_argument: {gone} finns inte"
