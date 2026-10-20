"""Elias tester: det Adrians tester inte täcker (prompten, Ctrl+C, kameran utan kamera, konstiga bildfiler)."""

import json
import sys

import cv2
import numpy as np

from spectrometer import main, plot, registry, session, source


class FakeCamera:
    """Låtsaskamera i stället för cv2.VideoCapture: ger bilderna i listan, en per read."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.reads = 0
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        self.reads += 1
        if self.released or not self.frames:
            return False, None
        item = self.frames.pop(0)
        if isinstance(item, BaseException):
            raise item
        return True, item

    def release(self):
        self.released = True


def use_camera(monkeypatch, frames):
    """Byter cv2.VideoCapture mot FakeCamera och ger kameran som programmet kommer att få."""
    cam = FakeCamera(frames)

    def fake_capture(index, backend):
        return cam

    monkeypatch.setattr(source.cv2, "VideoCapture", fake_capture)
    return cam


def line_image(column=12, value=200):
    """En bild 10 x 20 med en lodrät linje i en kolumn."""
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, column] = value
    return image


def new_state():
    """En ny state med standardinställningarna."""
    return session.new_state(session.DEFAULTS)


def run_prompt(monkeypatch, capsys, lines):
    """Kör main med raderna som om de skrevs vid prompten; ett undantag i listan kastas av input."""
    feed = iter(lines)

    def fake_input(prompt):
        print(prompt, end="")
        item = next(feed, EOFError())
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(sys, "argv", ["spectrometer.main"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)  # som en kommandofil: Fel: ger slutkod 1
    code = main.main()
    return code, capsys.readouterr().out


def error_text(state, line):
    """Kör en rad och ger felets text; ger None om raden inte gav fel."""
    try:
        registry.run_command(state, line)
    except (ValueError, RuntimeError, OSError) as error:
        return str(error)
    return None


def test_elias_one_line_per_error(monkeypatch, capsys):
    lines = ["foo", "roi 1 2 3", "frames tre", 'source file "x', "channel purple", "help x", "save", "quit"]
    code, out = run_prompt(monkeypatch, capsys, lines)
    errors = [row for row in out.splitlines() if "Fel:" in row]
    assert code == 1
    assert len(errors) == 7
    assert "Traceback" not in out
    assert "Fel: input.invalid_argument: N ska vara ett heltal, fick tre" in out
    assert "Fel: input.missing_data:" in out
    assert out.rstrip().endswith("Avslutar.")


def test_elias_ctrl_c_at_prompt(monkeypatch, capsys):
    code, out = run_prompt(monkeypatch, capsys, ["show", KeyboardInterrupt()])
    assert code == 0
    assert out.endswith("spektro> \n")
    assert "Avbrutet." not in out
    assert "Traceback" not in out


def test_elias_ctrl_c_during_step_releases_camera(monkeypatch, capsys):
    cam = use_camera(monkeypatch, [KeyboardInterrupt()])
    code, out = run_prompt(monkeypatch, capsys, ["source camera 0", "step", "show", "quit"])
    assert code == 0
    assert "spektro> Avbrutet." in out
    assert cam.released
    assert "Mätning: nej" in out
    assert out.rstrip().endswith("Avslutar.")


def test_elias_camera_minus_one():
    state = new_state()
    assert error_text(state, "source camera -1") == "input.invalid_argument: index ska vara minst 0"
    assert state["settings"]["source"] == ("camera", 0)


def test_elias_camera_word():
    state = new_state()
    assert error_text(state, "source camera x") == "input.invalid_argument: index ska vara ett heltal, fick x"


def test_elias_camera_too_big():
    state = new_state()
    assert error_text(state, "source camera 2147483648") is None
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed: kunde inte öppna /dev/video2147483648.")


def test_elias_live_loses_camera(monkeypatch):
    cam = use_camera(monkeypatch, [line_image(), line_image()])
    closed = []
    drawn = []
    win = {"fig": object()}
    monkeypatch.setattr(plot, "open_plot", lambda: win)
    monkeypatch.setattr(plot, "draw", lambda win, x, values, x_label, y_label: drawn.append(values))
    monkeypatch.setattr(plot, "is_open", lambda win: True)
    monkeypatch.setattr(plot, "pause", lambda seconds: None)
    monkeypatch.setattr(plot, "close", closed.append)
    state = new_state()
    registry.run_command(state, "source camera 0")
    text = error_text(state, "start")
    assert text.startswith("camera.read_failed:")
    assert len(drawn) == 2
    assert cam.released
    assert closed == [win]


def test_elias_gray_file(tmp_path):
    path = tmp_path / "gra.png"
    cv2.imwrite(str(path), np.full((4, 6), 80, dtype="uint8"))
    image = source.read_frame(source.open_source("file", path))
    assert image.shape == (4, 6, 3)
    assert np.all(image == 80)


def test_elias_bgra_file(tmp_path):
    path = tmp_path / "alfa.png"
    bgra = np.zeros((4, 6, 4), dtype="uint8")
    bgra[:, :] = (10, 20, 30, 128)
    cv2.imwrite(str(path), bgra)
    image = source.read_frame(source.open_source("file", path))
    assert image.shape == (4, 6, 3)
    assert tuple(image[0, 0]) == (10, 20, 30)


def test_elias_16bit_file(tmp_path):
    path = tmp_path / "sexton.png"
    cv2.imwrite(str(path), np.full((4, 6, 3), 1000, dtype="uint16"))
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "uint16" in text


def test_elias_text_file(tmp_path):
    path = tmp_path / "text.png"
    path.write_text("inte en bild", encoding="utf-8")
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "text.png" in text
    assert "None" not in text


def test_elias_missing_file(tmp_path):
    state = new_state()
    registry.run_command(state, f"source file {(tmp_path / 'finns_inte.png').as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "finns_inte.png" in text


def test_elias_vertical_and_folder(tmp_path, capsys):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[4, :] = 100
    path = tmp_path / "vagrat.png"
    cv2.imwrite(str(path), image)
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "axis vertical")
    registry.run_command(state, "step")
    registry.run_command(state, f"save {(tmp_path / 'data').as_posix()}")
    out = capsys.readouterr().out
    assert "Topp 100 vid pixel 4 (1 bild)" in out
    folders = list((tmp_path / "data").iterdir())
    assert len(folders) == 1
    assert sorted(p.name for p in folders[0].iterdir()) == ["raw.png", "settings.json", "spectrum.csv"]
    settings = json.loads((folders[0] / "settings.json").read_text(encoding="utf-8"))
    assert settings["axis"] == "vertical"
    rows = (folders[0] / "spectrum.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 11
    assert rows[5] == "4,100,true"


def test_elias_frames_reads_new_images(monkeypatch):
    cam = use_camera(monkeypatch, [line_image(value=v) for v in (90, 100, 110)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "frames 3")
    registry.run_command(state, "step")
    assert cam.reads == 3
    assert cam.released
    assert state["spectrum"]["values"][12] == 100
    assert state["image"][0, 12, 0] == 110


def test_elias_read_failure_releases_camera(monkeypatch):
    cam = use_camera(monkeypatch, [])
    state = new_state()
    registry.run_command(state, "source camera 0")
    text = error_text(state, "step")
    assert text == "camera.read_failed: kunde inte läsa en bild från kameran"
    assert cam.released
    assert state["spectrum"] is None


def test_elias_roi_kept_after_error(tmp_path):
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "roi 10 0 5 10")
    registry.run_command(state, "step")
    text = error_text(state, "roi 0 0 21 10")
    assert text.startswith("input.invalid_argument:")
    assert error_text(state, "roi 1 2 x 4") == "input.invalid_argument: width ska vara ett heltal, fick x"
    assert state["settings"]["roi"] == (10, 0, 5, 10)
    assert state["spectrum"] is not None



def test_elias_step_peak_only_inside_valid_range(tmp_path, capsys):
    """Största pixeln ligger utanför kalibreringens giltiga intervall; toppen ska vara den största giltiga."""
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 2] = 250  # störst, men hamnar utanför pixel_range
    image[:, 12] = 100  # giltig topp
    path = tmp_path / "tva.png"
    cv2.imwrite(str(path), image)
    pts = tmp_path / "p.csv"
    pts.write_text("pixel,wavelength_nm,check\n10,500,0\n14,540,0\n", encoding="utf-8")  # giltigt: pixel 6 till 18
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "channel red")
    registry.run_command(state, f"calibrate {pts.as_posix()}")
    capsys.readouterr()
    registry.run_command(state, "step")
    assert "Topp 100 vid våglängd (nm) 520 (1 bild)" in capsys.readouterr().out

def test_elias_unexpected_error_keeps_prompt(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SPEKTRO_DEBUG", raising=False)

    def krasch(state, src=None):
        raise ZeroDivisionError("division by zero")

    monkeypatch.setattr(main.measure, "measure", krasch)
    _code, out = run_prompt(monkeypatch, capsys, ["source file x.png", "step", "show", "quit"])
    assert "Fel: oväntat fel (ZeroDivisionError: division by zero), detaljer i logs/spektro.log" in out
    assert "Traceback" not in out
    assert out.rstrip().endswith("Avslutar.")
    assert "ZeroDivisionError" in (tmp_path / "logs" / "spektro.log").read_text(encoding="utf-8")
    for handler in list(main.log.handlers):
        main.log.removeHandler(handler)
        handler.close()



def saturated_file(tmp_path, name, blue=0, red=0):
    """En bildfil 10 x 20 med en röd linje i kolumn 12 och en blå i kolumn 3."""
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12, 2] = red
    image[:, 3, 0] = blue
    path = tmp_path / name
    cv2.imwrite(str(path), image)
    return path.as_posix()


def test_elias_saturation_only_counts_the_channel(tmp_path, capsys):
    """En mättad blå linje varnar inte när man mäter red, men gör det vid blue och gray."""
    state = new_state()
    registry.run_command(state, f"source file {saturated_file(tmp_path, 'bla.png', blue=255, red=100)}")
    registry.run_command(state, "channel red")
    registry.run_command(state, "step")
    assert "mättad" not in capsys.readouterr().out
    for channel in ("blue", "gray"):
        registry.run_command(state, f"channel {channel}")
        registry.run_command(state, "step")
        assert "Varning: mättad (255 i råbilden). Sänk exponeringen." in capsys.readouterr().out


def test_elias_saturation_in_any_frame(monkeypatch, capsys):
    """Första bilden är mättad, den sista inte: step varnar ändå, och spektrumet minns var."""
    use_camera(monkeypatch, [line_image(value=255), line_image(value=100)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, "frames 2")
    registry.run_command(state, "step")
    assert "Varning: mättad" in capsys.readouterr().out
    assert state["spectrum"]["saturated_px"] == 10
    assert np.flatnonzero(state["spectrum"]["saturated"]).tolist() == [12]


def test_elias_saturation_reference_response_and_save(tmp_path, capsys):
    """reference och response build varnar också; save skriver saturated_px före coefficients."""
    state = new_state()
    registry.run_command(state, f"source file {saturated_file(tmp_path, 'svart.png')}")
    registry.run_command(state, "dark 1")
    registry.run_command(state, f"source file {saturated_file(tmp_path, 'full.png', red=255)}")
    registry.run_command(state, "channel red")
    registry.run_command(state, "roi 10 0 3 2")
    capsys.readouterr()
    registry.run_command(state, "reference 1")
    assert "Varning: mättad" in capsys.readouterr().out
    pts = tmp_path / "p.csv"
    pts.write_text("pixel,wavelength_nm,check\n10,500,0\n12,520,0\n", encoding="utf-8")
    known = tmp_path / "k.csv"
    known.write_text("wavelength_nm,relative_power_per_nm\n490,1\n530,1\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {pts.as_posix()}")
    capsys.readouterr()
    registry.run_command(state, f"response build {known.as_posix()}")
    assert "Varning: mättad" in capsys.readouterr().out
    registry.run_command(state, "step")
    registry.run_command(state, f"save {(tmp_path / 'data').as_posix()}")
    folder = next((tmp_path / "data").iterdir())
    keys = list(json.loads((folder / "settings.json").read_text(encoding="utf-8")))
    assert keys.index("saturated_px") < keys.index("coefficients")
    assert json.loads((folder / "settings.json").read_text(encoding="utf-8"))["saturated_px"] == 2



def test_elias_stddev_kept_and_reversed_with_x(monkeypatch, tmp_path):
    """Spridningen mellan två bilder finns i spektrumet och vänds med x när våglängden faller längs pixlarna."""
    use_camera(monkeypatch, [line_image(value=90), line_image(value=110)])
    pts = tmp_path / "p.csv"
    pts.write_text("pixel,wavelength_nm,check\n10,540,0\n14,500,0\n", encoding="utf-8")  # fallande: x vänds
    state = new_state()
    registry.run_command(state, "source camera 0")
    registry.run_command(state, f"calibrate {pts.as_posix()}")
    registry.run_command(state, "frames 2")
    registry.run_command(state, "step")
    spectrum = state["spectrum"]
    assert np.argmax(spectrum["stddev"]) == np.argmax(spectrum["values"]) == 7  # pixel 12 räknat bakifrån
    assert np.nanmax(spectrum["stddev"]) == np.std([90, 110], ddof=1)


def test_elias_stddev_nan_for_one_frame(tmp_path):
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    assert np.all(np.isnan(state["spectrum"]["stddev"]))


def test_elias_stability_variation_and_drift(monkeypatch, capsys):
    cam = use_camera(monkeypatch, [line_image(value=v) for v in (90, 100, 110)])
    state = new_state()
    registry.run_command(state, "source camera 0")
    capsys.readouterr()
    registry.run_command(state, "stability 3")
    assert "stabilitet: 3 bilder, variation 10.0 %, drift +20.0 %" in capsys.readouterr().out
    assert cam.reads == 3
    assert cam.released
    assert state["spectrum"] is None
    assert error_text(state, "stability 2") == "input.invalid_argument: N ska vara minst 3"