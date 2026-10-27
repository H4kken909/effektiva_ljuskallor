import json

import cv2
import numpy as np
from helpers import line_image, new_state

from spectrometer.analysis import peaks
from spectrometer.core import registry, session


def say(capsys, state, command):
    registry.run_command(state, command)
    return capsys.readouterr().out.splitlines()


def test_echo_is_written_as_the_command(capsys):
    state = session.new_state(session.DEFAULTS)
    assert say(capsys, state, "source file x.png") == ["source file x.png"]
    assert say(capsys, state, 'source file "a b.png"') == ["source file a b.png"]
    assert say(capsys, state, "source camera 2") == ["source camera 2"]
    assert say(capsys, state, "roi 0 0 20 10")[-1].startswith("roi 0 0 20 10")
    assert say(capsys, state, "roi full") == ["roi full"]


def test_show_follows_the_commands(capsys, tmp_path):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    path = tmp_path / "image.png"
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f'source file "{path.as_posix()}"')
    registry.run_command(state, "roi 0 0 20 10")
    registry.run_command(state, "step")
    capsys.readouterr()
    rows = say(capsys, state, "show")
    assert f"file {path.as_posix()} · roi 0 0 20 10 · gray · direct" in rows
    assert "measurement yes" in rows[-1]


WAVELENGTHS = np.arange(380.0, 781.0)
X = np.arange(400.0, 700.1, 1.5)


def run(state, *lines):
    for line in lines:
        registry.run_command(state, line)


def measured_state(tmp_path, *lines):
    image = tmp_path / "line.png"
    cv2.imwrite(str(image), line_image())
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    run(state, f"source file {image.as_posix()}", *lines, "step")
    return state


def saved_folders(tmp_path):
    state = new_state()
    for value, note in ((200, "strong"), (100, "weak")):
        image = tmp_path / f"{note}.png"
        cv2.imwrite(str(image), line_image(value=value))
        run(state, f"source file {image.as_posix()}", f"note {note}", "step", f"save {(tmp_path / 'data').as_posix()}")
    return sorted(p.as_posix() for p in (tmp_path / "data").iterdir())


def led(tmp_path, name, center):
    folder = tmp_path / name
    folder.mkdir()
    sigma = 20.0 / 2.3548
    rows = ["x_nm,value,valid,raw_counts,stddev"] + [
        f"{a:g},{np.exp(-0.5 * ((a - center) / sigma) ** 2):.10g},true,0,0" for a in WAVELENGTHS
    ]
    (folder / "spectrum.csv").write_text("\r\n".join(rows) + "\r\n", encoding="utf-8")
    settings = {"use_response": True, "mode": "direct", "roi": [0, 0, 20, 10], "channel": "gray"}
    (folder / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return folder.as_posix()


def test_t07_fwhm_one_nm():
    x, y = np.array([500.0, 501.0, 502.0]), np.array([0.0, 2.0, 0.0])
    assert peaks.fwhm(x, y, 1) == 1.0


def test_fwhm_command(tmp_path, capsys):
    state = measured_state(tmp_path)
    run(state, "fwhm")
    rows = capsys.readouterr().out.splitlines()
    assert "peak 1: 12 pixel, height 200, FWHM 1 pixel" in rows


def test_color_command(capsys):
    state = new_state()
    planck = WAVELENGTHS**-5 / np.expm1(1.4388e7 / (WAVELENGTHS * 2856))
    state["spectrum"] = {"x": WAVELENGTHS, "values": planck / planck.max(), "mask": np.ones(WAVELENGTHS.size, dtype=bool),
                         "x_label": "wavelength (nm)", "y_label": "corrected signal (relative)"}
    run(state, "color")
    rows = capsys.readouterr().out.splitlines()
    assert rows[0] == "color: x 0.4475  y 0.4075  (CIE 1931 2°)"
    assert rows[1].startswith("color temperature: 2856 K")


def test_mix_command(tmp_path, capsys):
    folders = " ".join(led(tmp_path, name, center) for name, center in (("r", 630), ("g", 530), ("b", 460)))
    run(new_state(), f"mix {folders} --target 0.31 0.32")
    rows = capsys.readouterr().out.splitlines()
    assert rows[3].startswith("weights (relative, largest 1): R 1.000")
    assert rows[4] == "blend: x 0.3100  y 0.3200"
    run(new_state(), f"mix {folders} --cct 6500")
    assert "target: the blackbody curve at 6500 K" in capsys.readouterr().out


def test_series_and_note(tmp_path, capsys):
    state = measured_state(tmp_path, "series start red", "series note current_mA=10", "note red LED")
    run(state, "save", "series stop")
    text = capsys.readouterr().out
    assert "series red stopped" in text
    assert (tmp_path / "data" / "red" / "series.csv").exists()
    run(state, "note clear", "note")
    assert capsys.readouterr().out.splitlines()[-1] == "note: (none)"


def test_bandgap_command(capsys):
    state = new_state()
    values = 1 / (1 + np.exp((X - 550) / -4))
    state["spectrum"] = {"x": X, "values": values, "mask": np.isfinite(values),
                         "x_label": "wavelength (nm)", "y_label": "transmission (ratio)"}
    run(state, "bandgap")
    assert capsys.readouterr().out.startswith("bandgap: 2.248 ± 0.003 eV, the edge at 551.5 nm")


def test_compare_command(tmp_path, capsys):
    folders = saved_folders(tmp_path)
    capsys.readouterr()
    run(new_state(), "compare " + " ".join(folders))
    rows = capsys.readouterr().out.splitlines()
    assert rows[0].startswith("Relative numbers from the camera")


def test_figure_command(tmp_path):
    state = measured_state(tmp_path)
    target = tmp_path / "fig-01.png"
    run(state, f"figure {target.as_posix()}")
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert (tmp_path / "fig-01.txt").read_text(encoding="utf-8").startswith("Figure fig-01.png")


def test_load_command(tmp_path):
    state = measured_state(tmp_path)
    run(state, "save")
    folder = next((tmp_path / "data").iterdir())
    other = new_state()
    run(other, f"load {folder.as_posix()}")
    assert other["spectrum"]["values"][12] == 200
