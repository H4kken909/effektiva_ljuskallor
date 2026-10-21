"""plot.py med Agg: fönstret, temat och kurvan utan riktig skärm."""

import cv2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import KeyEvent
from matplotlib.colors import to_hex

from spectrometer import display, plot, registry, session

matplotlib.use("Agg")  # aldrig ett riktigt fönster i testerna, inte ens på en dator med skärm


def test_open_plot_morkt_tema():
    win = plot.open_plot()
    try:
        assert {"fig", "ax", "line"} <= win.keys()
        assert to_hex(win["fig"].get_facecolor()) == "#111827"
        assert to_hex(win["ax"].get_facecolor()) == "#1f2937"
        assert win["fig"].get_layout_engine() is not None
    finally:
        plot.close(win)


def test_draw_ljust_tema_titel_och_enhet():
    win = plot.open_plot()
    try:
        info = {"view": {"theme": "light"}, "name": "spektro - camera 0 - direct"}
        plot.draw(win, np.arange(5.0), np.ones(5), "pixel", "signal (counts)", info)
        assert to_hex(win["fig"].get_facecolor()) == "#ffffff"
        assert win["fig"].canvas.manager.get_window_title() == "spektro - camera 0 - direct"
        assert win["ax"].get_xlabel() == "pixel (läge i bilden)"
    finally:
        plot.close(win)


def test_draw_tva_ganger_en_linje():
    win = plot.open_plot()
    try:
        plot.draw(win, np.arange(5.0), np.ones(5), "pixel", "signal (counts)")
        plot.draw(win, np.arange(5.0), np.full(5, 2.0), "pixel", "signal (counts)")
        assert len(win["ax"].lines) == 1
        assert list(win["line"].get_ydata()) == [2.0] * 5
    finally:
        plot.close(win)


def test_draw_bara_nan():
    win = plot.open_plot()
    try:
        plot.draw(win, np.arange(5.0), np.full(5, np.nan), "pixel", "signal (counts)")
    finally:
        plot.close(win)


def test_theme_kommandot(capsys):
    state = session.new_state(session.DEFAULTS)
    assert state["view"]["theme"] == "dark"
    registry.run_command(state, "theme light")
    assert state["view"]["theme"] == "light"
    assert capsys.readouterr().out == "theme: light\n"
    try:
        registry.run_command(state, "theme blue")
    except ValueError as error:
        assert str(error) == "input.invalid_argument: theme tar ett ord, light eller dark"
    assert state["view"]["theme"] == "light"


def test_start_ger_fonstret_titel_och_vy(monkeypatch, tmp_path):
    path = tmp_path / "bild.png"
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    cv2.imwrite(str(path), image)
    win = {"fig": object()}

    def stop(win, x, values, x_label, y_label):
        raise KeyboardInterrupt

    monkeypatch.setattr(plot, "open_plot", lambda: win)
    monkeypatch.setattr(plot, "draw", stop)
    monkeypatch.setattr(plot, "is_open", lambda win: True)
    monkeypatch.setattr(plot, "close", lambda win: None)
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "start")
    assert win["name"] == f"spektro - file {path.as_posix()} - direct"
    assert win["view"] is state["view"]


def test_draw_rubrik_varning_referens_och_topp():
    win = plot.open_plot()
    try:
        x = np.arange(5.0)
        info = {"title": "fil a.png · roi hela bilden\nTopp 3 vid pixel 2", "warn": "MÄTTAD - sänk exponeringen",
                "ref": (x, np.full(5, 2.0)), "peak": ([2.0], [3.0]), "fixed_y": (0.0, 270.0), "foot": "mörker nej"}
        plot.draw(win, x, np.array([0, 1, 3, 1, 0.0]), "pixel", "signal (counts)", info)
        ax = win["ax"]
        assert ax.get_title(loc="left").endswith("Topp 3 vid pixel 2")
        assert ax.get_title(loc="right") == "MÄTTAD - sänk exponeringen"
        assert ax.get_ylim() == (0.0, 270.0)
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ["senaste mätningen", "referens"]
        lines = len(ax.lines)
        plot.draw(win, x, np.ones(5), "pixel", "signal (counts)", {"warn": None, "ref": None, "peak": None})
        assert ax.get_title(loc="right") == ""
        assert not win["ref_line"].get_visible()
        assert len(ax.lines) == lines
        assert ax.get_legend() is None
    finally:
        plot.close(win)


def test_draw_kamerabild_roi_ruta_och_remsa():
    win = plot.open_plot()
    try:
        image = np.zeros((20, 30, 3), dtype="uint8")
        image[8:12, :, 0] = 200  # blått band i BGR
        view = {"theme": "dark", "camera": True, "roi": True, "spectrum": True}
        info = {"image": image, "roi": (0, 8, 30, 4), "axis": "horizontal", "view": view}
        plot.draw(win, np.arange(30.0), np.ones(30), "pixel", "signal (counts)", info)
        assert win["camera_ax"].get_visible()
        assert win["camera_image"].get_array().shape == (20, 30, 3)
        assert tuple(win["camera_image"].get_array()[9, 0]) == (0, 0, 200)  # RGB: blått sist
        assert win["strip_image"].get_array().shape == (4, 30, 3)
        assert list(win["box_line"].get_ydata()) == [8, 8, 12, 12, 8]
        view["camera"] = False
        win["camera_time"] = -1.0
        plot.draw(win, np.arange(30.0), np.ones(30), "pixel", "signal (counts)")
        assert not win["camera_ax"].get_visible()
        assert win["strip_ax"].get_visible()
    finally:
        plot.close(win)


def test_view_kommandot(capsys):
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, "view camera off")
    registry.run_command(state, "view")
    assert capsys.readouterr().out.splitlines() == [
        "view camera: off", "view camera: off", "view roi: on", "view spectrum: on", "view normalize: off",
        "view xlim: auto", "view ylim: auto", "view compare: 0 kurvor", "view analysis: off",
    ]
    assert state["view"]["camera"] is False


def test_tangentkon_och_matplotlibs_tangenter_avstangda():
    win = plot.open_plot()
    try:
        assert win["keys"] == []
        assert plt.rcParams["keymap.save"] == []
        win["fig"].canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", win["fig"].canvas, "s"))
        assert win["keys"] == ["s"]
    finally:
        plot.close(win)


def test_draw_frusen_kurva_hjalp_paus_och_zoom():
    win = plot.open_plot()
    try:
        x = np.arange(5.0)
        info = {"frozen": (x, np.full(5, 2.0)), "frozen_label": "frusen 14:03:12", "help": "s spara · q stopp",
                "yscale": "zoom", "paused": True, "warn": "MÄTTAD - sänk exponeringen"}
        plot.draw(win, x, np.array([10.0, 20, 30, 20, 10]), "pixel", "signal (counts)", info)
        ax = win["ax"]
        assert win["frozen_line"].get_visible()
        assert [t.get_text() for t in ax.get_legend().get_texts()] == ["senaste mätningen", "frusen 14:03:12"]
        assert win["help_text"].get_visible()
        assert ax.get_ylim() == (8.0, 32.0)
        assert ax.get_title(loc="right") == "PAUS · p fortsätter"
        assert ax.get_title(loc="left").endswith(" · y zoom")
        plot.draw(win, x, np.ones(5), "pixel", "signal (counts)", {"frozen": None, "help": None, "paused": False})
        assert not win["frozen_line"].get_visible()
        assert not win["help_text"].get_visible()
    finally:
        plot.close(win)


def test_save_png_utan_fonster(tmp_path):
    before = plt.get_fignums()
    values = np.array([1.0, np.nan, 3.0, 2.0])
    plot.save_png(tmp_path / "spectrum.png", np.arange(4.0), values, "pixel", "signal (counts)", "20261020-120000")
    assert (tmp_path / "spectrum.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert plt.get_fignums() == before  # ingen pyplot-figur, inget fönster


def test_graf_visar_och_stanger(monkeypatch, tmp_path):
    shown = []
    monkeypatch.setattr(plot, "show", lambda: shown.append(plt.get_fignums()))
    state = session.new_state(session.DEFAULTS)
    try:
        registry.run_command(state, "graf")
    except ValueError as error:
        assert str(error) == "input.missing_data: Ingen mätning än. Kör step först."
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), np.full((10, 20, 3), 40, dtype="uint8"))
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    before = plt.get_fignums()
    registry.run_command(state, "graf")
    assert len(shown) == 1 and len(shown[0]) == len(before) + 1
    assert plt.get_fignums() == before


def test_view_granser_normering_jamforelse_och_panel(tmp_path, capsys):
    state = session.new_state(session.DEFAULTS)
    errors = []
    for line in ("view xlim 400 700", "view ylim auto", "view normalize on", "view analysis peaks",
                 "view xlim 5 1", "view ylim a b", "view analysis colour", "view analysis foo", "view compare add",
                 "view zoom on"):
        try:
            registry.run_command(state, line)
        except ValueError as error:
            errors.append(str(error))
    assert state["view"]["xlim"] == (400.0, 700.0)
    assert state["view"]["ylim"] is None
    assert state["view"]["normalize"] is True
    assert state["view"]["analysis"] == "colour"  # 1.2.16: colour finns
    assert errors == [
        "input.invalid_argument: view xlim: MIN ska vara mindre än MAX och båda ändliga",
        "input.invalid_argument: view ylim: MIN och MAX ska vara tal",
        "input.invalid_argument: okänd panel foo, välj peaks, calibration, transmission, response, colour, rgb, "
        "droop, edge, performance eller off",
        "input.missing_data: Ingen mätning än. Kör step först.",
        "input.invalid_argument: view zoom finns inte. Välj camera, roi, spectrum, normalize, xlim, ylim, compare "
        "eller analysis",
    ]
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), np.full((10, 20, 3), 40, dtype="uint8"))
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    registry.run_command(state, "view compare add")
    assert capsys.readouterr().out.splitlines()[-1].startswith("view compare: 1 kurvor, senast jämförelse 1 (")
    registry.run_command(state, "view compare clear")
    assert state["view"]["compare"] == []


def test_paneler_ur_state():
    state = session.new_state(session.DEFAULTS)
    x = np.arange(12.0)
    values = np.array([0.0, 1, 6, 1, 0, 0, 0, 0, 2, 9, 2, np.nan])
    spectrum = {"x": x, "y_label": "signal (counts)", "x_label": "pixel"}
    peaks = display.panel(state, "peaks", spectrum, values)
    assert list(peaks["points"][0]) == [9.0, 2.0]
    for name, why in (("calibration", "ingen kalibrering. Kör calibrate."), ("transmission", "ingen referens. Kör reference."),
                      ("response", "ingen respons. Kör response build."), ("droop", "inget resultat än. Kör series plot NAMN.")):
        empty = display.panel(state, name, spectrum, values)
        assert (empty["lines"], empty["text"]) == ([], f"otillgängligt: {why}")
    state["coefficients"] = np.array([400.0, 10.0])
    state["pixel_range"] = (0.0, 5.0)
    calibration = display.panel(state, "calibration", spectrum, values)
    assert calibration["text"] == "a0 400, a1 10\ngiltigt: pixel 0 till 5"
    assert calibration["lines"][0][1][-1] == 450.0


def test_draw_panel_jamforelse_och_granser():
    win = plot.open_plot()
    try:
        x = np.arange(5.0)
        view = {"theme": "dark", "xlim": (1.0, 3.0), "ylim": (0.0, 50.0)}
        panel = {"title": "peaks: toppar i kurvan", "x_label": "pixel", "lines": [(x, x, "kurvan")],
                 "points": ([2.0], [2.0]), "text": "x värde"}
        info = {"view": view, "panel": panel, "compare": [(x, np.full(5, 3.0), "jämförelse 1 (12:00:00)")]}
        plot.draw(win, x, np.ones(5), "pixel", "signal (counts)", info)
        assert win["panel_ax"].get_title(loc="left") == "peaks: toppar i kurvan"
        assert len(win["panel_ax"].lines) == 2
        assert win["panel_ax"].texts[0].get_text() == "x värde"
        assert win["ax"].get_xlim() == (1.0, 3.0)
        assert win["ax"].get_ylim() == (0.0, 50.0)
        assert "jämförelse 1 (12:00:00)" in [t.get_text() for t in win["ax"].get_legend().get_texts()]
    finally:
        plot.close(win)
