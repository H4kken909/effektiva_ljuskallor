"""Elias tester: det Adrians tester inte täcker (prompten, Ctrl+C, kameran utan kamera, konstiga bildfiler)."""

import json
import sys

import cv2
import numpy as np

from spectrometer import main, source


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
    code = main.main()
    return code, capsys.readouterr().out


def error_text(state, line):
    """Kör en rad och ger felets text; ger None om raden inte gav fel."""
    try:
        main.run_command(state, line)
    except (ValueError, RuntimeError, OSError) as error:
        return str(error)
    return None


def test_elias_one_line_per_error(monkeypatch, capsys):
    lines = ["foo", "roi 1 2 3", "frames tre", 'source file "x', "channel purple", "help x", "save", "quit"]
    code, out = run_prompt(monkeypatch, capsys, lines)
    errors = [row for row in out.splitlines() if "Fel:" in row]
    assert code is None
    assert len(errors) == 7
    assert "Traceback" not in out
    assert "Fel: input.invalid_argument: N ska vara ett heltal, fick tre" in out
    assert "Fel: input.missing_data:" in out
    assert out.rstrip().endswith("Avslutar.")


def test_elias_ctrl_c_at_prompt(monkeypatch, capsys):
    code, out = run_prompt(monkeypatch, capsys, ["show", KeyboardInterrupt()])
    assert code is None
    assert out.endswith("spektro> \n")
    assert "Avbrutet." not in out
    assert "Traceback" not in out


def test_elias_ctrl_c_during_step_releases_camera(monkeypatch, capsys):
    cam = use_camera(monkeypatch, [KeyboardInterrupt()])
    code, out = run_prompt(monkeypatch, capsys, ["source camera 0", "step", "show", "quit"])
    assert code is None
    assert "spektro> Avbrutet." in out
    assert cam.released
    assert "Mätning: nej" in out
    assert out.rstrip().endswith("Avslutar.")


def test_elias_camera_minus_one():
    state = main.new_state(main.DEFAULTS)
    assert error_text(state, "source camera -1") == "input.invalid_argument: index ska vara minst 0"
    assert state["settings"]["source"] == ("camera", 0)


def test_elias_camera_word():
    state = main.new_state(main.DEFAULTS)
    assert error_text(state, "source camera x") == "input.invalid_argument: index ska vara ett heltal, fick x"


def test_elias_camera_too_big():
    state = main.new_state(main.DEFAULTS)
    assert error_text(state, "source camera 2147483648") is None
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed: kunde inte öppna /dev/video2147483648.")


def test_elias_live_loses_camera(monkeypatch):
    cam = use_camera(monkeypatch, [line_image(), line_image()])
    closed = []
    drawn = []
    fig = type("Fig", (), {"number": 1})()
    monkeypatch.setattr(main.plot, "open_plot", lambda: {"fig": fig})
    monkeypatch.setattr(main.plot, "draw", lambda win, x, values, x_label, y_label: drawn.append(values))
    monkeypatch.setattr(main.plt, "fignum_exists", lambda number: True)
    monkeypatch.setattr(main.plt, "pause", lambda seconds: None)
    monkeypatch.setattr(main.plt, "close", closed.append)
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, "source camera 0")
    text = error_text(state, "start")
    assert text.startswith("camera.read_failed:")
    assert len(drawn) == 2
    assert cam.released
    assert closed == [fig]


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
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, f"source file {path.as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "uint16" in text


def test_elias_text_file(tmp_path):
    path = tmp_path / "text.png"
    path.write_text("inte en bild", encoding="utf-8")
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, f"source file {path.as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "text.png" in text
    assert "None" not in text


def test_elias_missing_file(tmp_path):
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, f"source file {(tmp_path / 'finns_inte.png').as_posix()}")
    text = error_text(state, "step")
    assert text.startswith("camera.open_failed:")
    assert "finns_inte.png" in text


def test_elias_vertical_and_folder(tmp_path, capsys):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[4, :] = 100
    path = tmp_path / "vagrat.png"
    cv2.imwrite(str(path), image)
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, f"source file {path.as_posix()}")
    main.run_command(state, "axis vertical")
    main.run_command(state, "step")
    main.run_command(state, f"save {(tmp_path / 'data').as_posix()}")
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
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, "source camera 0")
    main.run_command(state, "frames 3")
    main.run_command(state, "step")
    assert cam.reads == 3
    assert cam.released
    assert state["spectrum"]["values"][12] == 100
    assert state["image"][0, 12, 0] == 110


def test_elias_read_failure_releases_camera(monkeypatch):
    cam = use_camera(monkeypatch, [])
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, "source camera 0")
    text = error_text(state, "step")
    assert text == "camera.read_failed: kunde inte läsa en bild från kameran"
    assert cam.released
    assert state["spectrum"] is None


def test_elias_roi_kept_after_error(tmp_path):
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = main.new_state(main.DEFAULTS)
    main.run_command(state, f"source file {path.as_posix()}")
    main.run_command(state, "roi 10 0 5 10")
    main.run_command(state, "step")
    text = error_text(state, "roi 0 0 21 10")
    assert text.startswith("input.invalid_argument:")
    assert error_text(state, "roi 1 2 x 4") == "input.invalid_argument: width ska vara ett heltal, fick x"
    assert state["settings"]["roi"] == (10, 0, 5, 10)
    assert state["spectrum"] is not None
