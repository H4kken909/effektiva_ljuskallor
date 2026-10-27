import time

import cv2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from helpers import line_image, tk_window

from spectrometer.core import out, registry, session
from spectrometer.live import live
from spectrometer.visual import plot

matplotlib.use("Agg")


def test_save_png_gives_a_png_file(tmp_path):
    values = np.array([1.0, np.nan, 3.0, 2.0])
    plot.save_png(tmp_path / "spectrum.png", np.arange(4.0), values, "pixel", "signal (counts)", "20261020-120000")
    assert (tmp_path / "spectrum.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert plt.get_fignums() == []


def pump(window, seconds):
    end = time.perf_counter() + seconds
    while time.perf_counter() < end and not window.closing:
        window._tick()
        window.root.update()
        time.sleep(0.005)


def test_window_runs_commands_and_live(monkeypatch, tmp_path):
    path = tmp_path / "image.png"
    image = np.zeros((40, 60, 3), dtype="uint8")
    image[10:30, 30] = 220
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    window = tk_window(state)
    monkeypatch.setattr(live, "HOST", window)
    out.set_sink(window)

    def write(line):
        window._set_line(line)
        window._enter()

    try:
        window.show_prompt()
        for line in (f"source file {path.as_posix()}", "roi 0 10 60 20", "start 0.5"):
            write(line)
        pump(window, 1.0)
        assert window.draws > 0 and state["spectrum"] is not None
        assert window.win["peak"][0][0] == 30.0
        write("save")
        assert len(list((tmp_path / "data").iterdir())) == 1
        write("quit")
        assert window.closing
        assert "Saved in " in window.console.get("1.0", "end")
    finally:
        out.set_sink(None)
        window.stop_live()
        window.root.destroy()


def run_live(monkeypatch, tmp_path, image, before=()):
    cv2.imwrite(str(tmp_path / "image.png"), image)
    cv2.imwrite(str(tmp_path / "black.png"), np.zeros_like(image))
    win = {"fig": object()}
    drawn = []

    def draw(win, x, values, x_label, y_label):
        drawn.append((x, values, x_label, y_label))
        if len(drawn) >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(plot, "open_plot", lambda: win)
    monkeypatch.setattr(plot, "draw", draw)
    monkeypatch.setattr(plot, "is_open", lambda win: True)
    monkeypatch.setattr(plot, "pause", lambda seconds: None)
    monkeypatch.setattr(plot, "close", lambda win: None)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in [*before, f"source file {(tmp_path / 'image.png').as_posix()}", "start"]:
        registry.run_command(state, line.replace("BLACK", (tmp_path / "black.png").as_posix()))
    return win, drawn, state


def test_live_draws_spectrum_several_rounds(monkeypatch, tmp_path):
    win, drawn, _state = run_live(monkeypatch, tmp_path, line_image())
    assert len(drawn) == 3
    assert "Peak 200 at pixel 12" in win["title"]
    assert drawn[-1][1][12] == 200


def test_live_warns_on_saturated(monkeypatch, tmp_path):
    win, _drawn, _state = run_live(monkeypatch, tmp_path, line_image(value=255))
    assert win["warn"] == "SATURATED - lower the exposure"


def test_live_transmission(monkeypatch, tmp_path):
    before = ["source file BLACK", "dark 1", f"source file {(tmp_path / 'image.png').as_posix()}", "reference 1",
              "mode transmission"]
    win, drawn, _state = run_live(monkeypatch, tmp_path, line_image(), before)
    assert drawn[-1][3] == "transmission (ratio)"
    assert win["guide"][1] == [1.0, 1.0]


def test_save_after_live_saves_last_curve(monkeypatch, tmp_path):
    _win, _drawn, state = run_live(monkeypatch, tmp_path, line_image())
    registry.run_command(state, "save")
    folder = next((tmp_path / "data").iterdir())
    assert (folder / "spectrum.csv").exists()
