"""1.2.8 Blandning: mapp.read läser en sparad mätning, mix ger vikterna för tre LED (Krav 19a, 19b). Relativt."""

import json

import cv2
import numpy as np
from test_elias import error_text, line_image, new_state

from spectrometer import registry
from spectrometer.analysis import color, mapp


def led(tmp_path, name, center, fwhm=20.0, **settings):
    """En sparad LED-mätning: gaussisk topp vid center nm, x_nm 380–780 i steg om 2, CRLF som csv.writer skriver."""
    folder = tmp_path / name
    folder.mkdir()
    x = np.arange(380.0, 781.0, 2.0)
    rows = ["x_nm,value,valid"] + [f"{a:g},{b:.10g},true" for a, b in zip(x, color.gaussian(x, center, fwhm))]
    (folder / "spectrum.csv").write_text("\r\n".join(rows) + "\r\n", encoding="utf-8")
    saved = {"use_response": True, "mode": "direct", "roi": [0, 0, 20, 10], "channel": "gray"} | settings
    (folder / "settings.json").write_text(json.dumps(saved), encoding="utf-8")
    return folder.as_posix()


def rgb(tmp_path):
    """Tre LED: röd 630, grön 530 och blå 460 nm, FWHM 20 nm."""
    return " ".join(led(tmp_path, name, center) for name, center in (("r", 630), ("g", 530), ("b", 460)))


def run(capsys, line):
    """Kör en rad och ger raderna som skrevs."""
    registry.run_command(new_state(), line)
    return capsys.readouterr().out.splitlines()


def test_read_saved_measurement(tmp_path, capsys):
    """ANA-02: mapp.read läser det save skriver: x_px utan kalibrering, tom cell blir NaN och ogiltig."""
    image = tmp_path / "linje.png"
    cv2.imwrite(str(image), line_image())
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in (f"source file {image.as_posix()}", "step", "save"):
        registry.run_command(state, line)
    saved = mapp.read(state["spectrum"]["saved_in"])
    assert saved["x_label"] == "pixel" and saved["x"][12] == 12 and saved["values"][12] == 200
    assert saved["mask"].all() and saved["settings"]["channel"] == "gray"
    lonely = tmp_path / "ensam.csv"
    lonely.write_text("x_px,value,valid\n0,,false\n1,5,true\n", encoding="utf-8")
    capsys.readouterr()
    saved = mapp.read(lonely)
    assert np.isnan(saved["values"][0]) and saved["mask"].tolist() == [False, True] and saved["settings"] == {}
    assert capsys.readouterr().out.startswith("Varning: settings.json saknas i ")


def test_mix_target_white(tmp_path, capsys):
    """KRV-25: vikterna för kallt vitt; blandningen hamnar på målet och nära svartkroppskurvan."""
    assert run(capsys, f"mix {rgb(tmp_path)} --target 0.31 0.32") == [
        "R: x 0.7014  y 0.2986",
        "G: x 0.1661  y 0.7871",
        "B: x 0.1431  y 0.0338",
        "vikter (relativa, största 1): R 1.000  G 0.842  B 0.732",
        "blandningen: x 0.3100  y 0.3200",
        "färgtemperatur: 6736 K (McCamy; avstånd till svartkroppskurvan 0.0002 i uv)",
    ]


def test_mix_outside_the_triangle_and_cct(tmp_path, capsys):
    folders = rgb(tmp_path)
    rows = run(capsys, f"mix {folders} --target 0.1 0.8")
    assert rows[-1] == "Varning: negativ vikt: målet ligger utanför triangeln, de tre LED:erna räcker inte"
    rows = run(capsys, f"mix {folders} --cct 4000")
    assert rows[3] == "mål: svartkroppskurvan vid 4000 K, x 0.3805  y 0.3769"
    assert rows[-2] == "blandningen: x 0.3805  y 0.3769"


def test_mix_sweep(tmp_path, capsys):
    """KRV-26: en rad per färg; en blå LED vid 490 nm räcker inte till sRGB:s blå."""
    rows = run(capsys, f"mix {rgb(tmp_path)} --sweep")
    assert rows[3] == "färg        x       y       R       G       B       räcker"
    assert rows[4] == "röd         0.6400  0.3300   1.000   0.080   0.017  ja"
    assert len(rows) == 3 + 1 + len(color.TARGETS)  # tre LED, rubriken och en rad per färg
    folders = " ".join(led(tmp_path, n, c) for n, c in (("r2", 630), ("g2", 530), ("b2", 490)))
    rows = run(capsys, f"mix {folders} --sweep")
    assert next(row for row in rows if row.startswith("blå ")).endswith("nej")


def test_mix_fwhm_narrow_lines_cover_more(tmp_path, capsys):
    """KRV-27: smalare linjer ger större triangel; FWHM 20 nm ger samma triangel som de mätta (som är 20 nm)."""
    folders = rgb(tmp_path)
    areas = []
    for width in (10, 20, 40):
        rows = run(capsys, f"mix {folders} --fwhm {width}")
        assert rows[3] == "toppar: R 630.0 nm, G 530.0 nm, B 460.0 nm"
        measured, model = (float(part.split()[-1]) for part in rows[4].split(","))
        areas.append(model)
    assert areas[0] > areas[1] > areas[2]
    assert abs(areas[1] - measured) < 1e-3


def test_mix_refuses_and_warns(tmp_path, capsys):
    folders = rgb(tmp_path)
    raw = led(tmp_path, "rå", 600, use_response=False)
    state = new_state()
    assert error_text(state, f"mix {raw} {folders.split()[1]} {folders.split()[2]} --sweep") == (
        f"input.missing_data: {raw}: inte responskorrigerad (spara med response on i mode direct)"
    )
    assert error_text(state, f"mix {folders}") == (
        "input.invalid_argument: mix: tre mätmappar och --target X Y, --cct K, --sweep eller --fwhm W"
    )
    assert error_text(state, f"mix {folders} --mal 0.3 0.3").startswith("input.invalid_argument: mix: okänt val --mal")
    assert error_text(state, f"mix {folders} --target 0.6 0.5") == "input.invalid_argument: X + Y ska vara mindre än 1"
    other = led(tmp_path, "annan", 630, channel="red")
    capsys.readouterr()
    rows = run(capsys, f"mix {other} {folders.split()[1]} {folders.split()[2]} --sweep")
    assert rows[0] == "Varning: mätningarna skiljer sig i channel; vikterna jämför då olika saker"
