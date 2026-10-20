"""start (live) med låtsasfönster: rubrik, MÄTTAD, bilder/s och referens, utan riktigt fönster och utan kamera."""

import cv2
import numpy as np

from spectrometer import measure, plot, registry, session, source


def line_image(column=12, value=200):
    """En bild 10 x 20 med en lodrät linje i en kolumn."""
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, column] = value
    return image


def live(monkeypatch, tmp_path, image, before=(), laps=3, win=None, later=()):
    """Kör start på bildfilen image efter raderna i before; draw kastar KeyboardInterrupt vid varv laps.

    Ger (win, drawn, state); drawn är argumenten till varje plot.draw.
    """
    cv2.imwrite(str(tmp_path / "bild.png"), image)
    cv2.imwrite(str(tmp_path / "svart.png"), np.zeros_like(image))
    win = {"fig": object()} if win is None else win
    drawn = []

    def draw(win, x, values, x_label, y_label):
        drawn.append((x.copy(), values.copy(), x_label, y_label))
        if len(drawn) >= laps:
            raise KeyboardInterrupt

    monkeypatch.setattr(plot, "open_plot", lambda: win)
    monkeypatch.setattr(plot, "draw", draw)
    monkeypatch.setattr(plot, "is_open", lambda win: True)
    later = list(later)

    def pause(seconds):
        if later:
            win.setdefault("keys", []).append(later.pop(0))

    monkeypatch.setattr(plot, "pause", pause)
    monkeypatch.setattr(plot, "close", lambda win: None)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    for line in [*before, f"source file {(tmp_path / 'bild.png').as_posix()}", "start"]:
        registry.run_command(state, line.replace("SVART", (tmp_path / "svart.png").as_posix()))
    return win, drawn, state


def test_live_rubrik_topp_och_bilder_per_sekund(monkeypatch, tmp_path):
    win, drawn, _state = live(monkeypatch, tmp_path, line_image())
    assert len(drawn) == 3
    assert win["title"].startswith("fil ")
    assert "Topp 200 vid pixel 12" in win["title"]
    assert "bilder/s" in win["title"]
    assert win["warn"] is None
    assert win["peak"] == ([12.0], [200.0])
    assert win["fixed_y"] == (0.0, 270.0)
    assert win["foot"].endswith("frames 1 · mättad nej")


def test_live_mattad_i_rubriken(monkeypatch, tmp_path):
    win, _drawn, _state = live(monkeypatch, tmp_path, line_image(value=255))
    assert win["warn"] == "MÄTTAD - sänk exponeringen"
    assert win["status"].endswith("MÄTTAD - sänk exponeringen")


def test_live_referensen_som_egen_linje(monkeypatch, tmp_path):
    before = ["source file SVART", "dark 1", f"source file {(tmp_path / 'bild.png').as_posix()}", "reference 1"]
    win, drawn, _state = live(monkeypatch, tmp_path, line_image(), before)
    ref_x, ref_values = win["ref"]
    np.testing.assert_array_equal(ref_x, drawn[-1][0])
    assert ref_values[12] == 200


def test_live_transmission_fast_y_och_100_procent(monkeypatch, tmp_path):
    before = ["source file SVART", "dark 1", f"source file {(tmp_path / 'bild.png').as_posix()}", "reference 1",
              "mode transmission"]
    win, drawn, _state = live(monkeypatch, tmp_path, line_image(), before)
    assert drawn[-1][3] == "transmission (kvot)"
    assert win["ref"] is None
    assert win["fixed_y"] == (0.0, 1.2)
    assert win["guide"][1] == [1.0, 1.0]


def test_live_mattad_foljer_vald_kanal(monkeypatch, tmp_path, capsys):
    """Bara grön är 255: MÄTTAD i live för green och gray men inte för red, precis som varningen i step."""
    image = line_image(value=0)
    image[:, 12, 1] = 255  # BGR: index 1 är grön
    for channel, full in (("green", True), ("gray", True), ("red", False)):
        win, _drawn, state = live(monkeypatch, tmp_path, image, [f"channel {channel}"])
        capsys.readouterr()
        registry.run_command(state, "step")
        assert ("Varning: mättad" in capsys.readouterr().out) is full
        assert (win["warn"] == "MÄTTAD - sänk exponeringen") is full
        assert win["foot"].endswith(f"mättad {'ja' if full else 'nej'}")


class Camera:
    """Låtsaskamera för cv2.VideoCapture: samma bild vid varje read; räknar read och release."""

    def __init__(self, image):
        self.image = image
        self.reads = 0
        self.released = 0

    def isOpened(self):
        return True

    def read(self):
        self.reads += 1
        return True, self.image.copy()

    def release(self):
        self.released += 1


def test_live_s_sparar_som_save(monkeypatch, tmp_path, capsys):
    _win, drawn, _state = live(monkeypatch, tmp_path, line_image(), win={"fig": object(), "keys": ["s"]})
    folders = list((tmp_path / "data").iterdir())
    assert len(folders) == 1
    assert sorted(p.name for p in folders[0].iterdir()) == ["README.txt", "raw.png", "settings.json", "spectrum.csv", "spectrum.png"]
    assert f"Sparad i {folders[0].as_posix()}" in capsys.readouterr().out
    assert len(drawn) == 3


def test_live_q_och_ctrl_c_stoppar(monkeypatch, tmp_path, capsys):
    for key in ("q", "ctrl+c"):
        _win, drawn, _state = live(monkeypatch, tmp_path, line_image(), win={"fig": object(), "keys": [key]})
        assert len(drawn) == 1
        assert capsys.readouterr().out.endswith("live stoppad\n")


def test_live_paus_mater_inte_men_fonstret_lever(monkeypatch, tmp_path):
    counted = []
    real = measure.measure
    monkeypatch.setattr(measure, "measure", lambda state, src=None: counted.append(1) or real(state, src))
    win, drawn, _state = live(monkeypatch, tmp_path, line_image(), laps=6, later=["f", "p"],
                              win={"fig": object(), "keys": ["p"]})
    assert len(drawn) == 6
    assert len(counted) == 3  # varv 1 (paus med f och p ritar om utan mätning), varv 2 och 3
    assert win["paused"] is False
    np.testing.assert_array_equal(win["frozen"][1], drawn[0][1])


def test_live_visningstangenter(monkeypatch, tmp_path):
    keys = ["y", "n", "h", "y"]  # varje tangent ritar om, så 8 ritningar räcker till fyra tangenter och tre varv till
    win, drawn, state = live(monkeypatch, tmp_path, line_image(), laps=8, win={"fig": object(), "keys": keys})
    assert win["yscale"] == "zoom"
    assert state["view"]["normalize"] is True
    assert win["help"].startswith("s spara")
    assert drawn[-1][3] == "normerad (relativ)"
    assert np.nanmax(drawn[-1][1]) == 1.0
    assert win["fixed_y"] == (0.0, 1.1)


def test_live_kameran_oppnas_en_gang_och_stangs_fore_fonstret(monkeypatch):
    cam = Camera(line_image())
    opened = []
    events = []

    def capture(index, backend):
        opened.append(index)
        return cam

    monkeypatch.setattr(source.cv2, "VideoCapture", capture)
    monkeypatch.setattr(plot, "open_plot", lambda: {"fig": object()})
    monkeypatch.setattr(plot, "draw", lambda win, x, values, x_label, y_label: None)
    monkeypatch.setattr(plot, "is_open", lambda win: cam.reads < 3)
    monkeypatch.setattr(plot, "pause", lambda seconds: None)
    monkeypatch.setattr(plot, "close", lambda win: events.append(("close", cam.released)))
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, "frames 2")
    registry.run_command(state, "start")
    assert opened == [0]
    assert cam.reads == 4  # två varv med två bilder
    assert events == [("close", 1)]  # kameran släppt före fönstret


def test_save_efter_start_ger_sista_kurvan(monkeypatch, tmp_path):
    _win, drawn, state = live(monkeypatch, tmp_path, line_image())
    registry.run_command(state, "save")
    folder = next((tmp_path / "data").iterdir())
    rows = (folder / "spectrum.csv").read_text(encoding="utf-8").splitlines()[1:]
    assert [row.split(",")[1] for row in rows] == [f"{v:.10g}" if np.isfinite(v) else "" for v in drawn[-1][1]]


def test_live_axeltexter_efter_calibrate(monkeypatch, tmp_path):
    points = tmp_path / "p.csv"
    points.write_text("pixel,wavelength_nm,check\n10,500,0\n14,540,0\n", encoding="utf-8")
    before = [f"calibrate {points.as_posix()}"]
    _win, drawn, _state = live(monkeypatch, tmp_path, line_image(), before)
    _x, values, x_label, y_label = drawn[-1]
    assert (x_label, y_label) == ("våglängd (nm)", "signal (counts)")
    assert np.isnan(values[0])  # pixel 0 ligger utanför det giltiga intervallet (6 till 18)


def test_live_med_analyspanel_och_jamforelse(monkeypatch, tmp_path):
    before = [f"source file {(tmp_path / 'bild.png').as_posix()}", "step", "view compare add", "view analysis peaks"]
    win, _drawn, _state = live(monkeypatch, tmp_path, line_image(), before)
    assert win["panel"]["title"] == "peaks: toppar i kurvan"
    assert list(win["panel"]["points"][0]) == [12.0]
    assert [label for _x, _y, label in win["compare"]][0].startswith("jämförelse 1 (")
