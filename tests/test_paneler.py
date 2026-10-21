"""1.2.16 Figurer och panelerna: figure --cie och analyspanelerna colour, rgb, droop, edge och performance (Agg)."""

import cv2
import matplotlib
import numpy as np
from test_bandgap import edge_at, transmission_state
from test_blandning import rgb
from test_elias import error_text, line_image, new_state
from test_farg import measured

from spectrometer import display, plot, registry
from spectrometer.analysis import color, series

matplotlib.use("Agg")  # aldrig ett riktigt fönster i testerna

LAM = np.arange(380.0, 781.0)


def glow_lamp():
    """State med en mätning av Planck 2856 K (kalibrerad, response on), som en glödlampa."""
    planck = color.planck(LAM, 2856)
    state = measured(planck / planck.max())
    state["spectrum"].update(x_label="våglängd (nm)", y_label="korrigerad signal (relativ)")
    return state


def panel_of(state, name):
    """Panelen name för senaste mätningen i state."""
    spectrum = state["spectrum"]
    return display.panel(state, name, spectrum, np.where(spectrum["mask"], spectrum["values"], np.nan))


def test_figure_cie_of_the_latest_measurement(tmp_path, capsys):
    """KRV-23/RAP-11: hästskon, Planck-kurvan och punkten för senaste mätningen; UT.txt med x, y och villkoren."""
    target = tmp_path / "cie.png"
    registry.run_command(glow_lamp(), f"figure {target.as_posix()} --cie")
    caption = target.with_suffix(".txt")
    assert capsys.readouterr().out.splitlines() == [
        f"Sparad: {target.as_posix()} och {caption.as_posix()} (villkoren till bildtexten)"
    ]
    assert abs(cv2.imread(str(target)).shape[1] - 12 / 2.54 * 200) < 2  # 12 cm vid 200 dpi
    rows = caption.read_text(encoding="utf-8").splitlines()
    assert rows[0] == (f"Figur {target.name}: CIE 1931 xy (2°), spektralkurvan ur programmets tabell 380–700 nm, "
                       "Planck-kurvan 1000–20000 K")
    assert rows[1].startswith("senaste mätningen: x 0.4475  y 0.4075; mapp inte sparad")
    assert rows[-1] == "Färgen ur responskorrigerade relativa tal; inte watt, lumen eller verkningsgrad."


def test_figure_cie_of_three_leds_and_refusals(tmp_path):
    """Tre sparade LED (R, G, B) ger tre punkter och triangeln; utan respons, med --norm eller utan nm: Fel-rad."""
    target = tmp_path / "rgb.svg"
    registry.run_command(new_state(), f"figure {target.as_posix()} --cie {rgb(tmp_path)}")
    assert target.stat().st_size > 1000
    rows = target.with_suffix(".txt").read_text(encoding="utf-8").splitlines()
    assert [row.split(":")[0] for row in rows[1:4]] == ["r", "g", "b"]
    state = glow_lamp()
    state["use_response"] = False
    assert error_text(state, "figure f.png --cie") == (
        "input.missing_data: figure --cie kräver response on i mode direct (annars är det kamerans färg)"
    )
    assert error_text(glow_lamp(), "figure f.png --cie --norm") == (
        "input.invalid_argument: figure --cie går inte med --norm, --log, --ev eller --xlim"
    )


def test_colour_panel_shows_what_color_computed(capsys):
    """colour: punkten, hästskon och Planck-kurvan; CCT och Duv i tabellen. Före color: otillgängligt, aldrig påhittat."""
    state = glow_lamp()
    assert panel_of(state, "colour")["text"] == "otillgängligt: inget resultat än. Kör color."
    registry.run_command(state, "color")
    panel = panel_of(state, "colour")
    assert panel["title"] == "colour: CIE 1931 xy" and panel["equal"]
    assert [round(v[0], 4) for v in panel["points"]] == [0.4475, 0.4075]
    assert panel["text"] == "x 0.4475  y 0.4075\nCCT 2856 K\nDuv +0.0000"
    assert [line[2] for line in panel["lines"]] == ["spektralkurvan", "Planck"]


def test_rgb_panel_after_mix(tmp_path, capsys):
    """rgb: de tre LED:erna, triangeln och blandningen; vikterna i tabellen. --sweep: målfärgerna och om de räcker."""
    folders = rgb(tmp_path)
    state = new_state()
    registry.run_command(state, f"mix {folders} --target 0.31 0.32")
    panel = display.panel(state, "rgb", None, None)
    assert len(panel["points"][0]) == 4
    assert panel["text"].splitlines()[-1] == "vikter R 1.000 G 0.842 B 0.732"
    registry.run_command(state, f"mix {folders} --sweep")
    rows = display.panel(state, "rgb", None, None)["text"].splitlines()
    assert rows[3] == "röd: räcker" and len(rows) == 3 + len(color.TARGETS)


def test_droop_panel_after_series_plot(tmp_path, capsys):
    """droop: relativ uteffekt och area/I mot strömmen, droop i procent i tabellen."""
    folder = tmp_path / "data" / "led"
    folder.mkdir(parents=True)
    for current in (10, 20, 40, 80):
        series.append(folder / "serie.csv", {"current_mA": current, "area": 0.8 * current / (1 + current / 40)})
    state = new_state()
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    registry.run_command(state, f"series plot led {(tmp_path / 'led.png').as_posix()}")
    panel = display.panel(state, "droop", None, None)
    assert [line[2] for line in panel["lines"]] == ["led uteffekt", "led area/I"]
    assert panel["lines"][0][1][-1] == 1 and panel["text"].splitlines()[0] == "led: droop 58 %"


def test_edge_panel_after_bandgap(capsys):
    """edge: absorbansen mot fotonenergin och kanten som bandgap fann; brantaste lutningen eller två räta linjer."""
    state = transmission_state(edge_at(550))
    registry.run_command(state, "bandgap")
    panel = display.panel(state, "edge", None, None)
    assert panel["title"] == "edge: brantaste lutningen" and panel["text"] == "E_g 2.248 eV\n551.5 nm"
    line_E, line_A = panel["lines"][1][:2]
    assert line_A[0] == 0 and line_E[0] == panel["points"][0][0]
    registry.run_command(state, "bandgap --anpassa")
    panel = display.panel(state, "edge", None, None)
    assert panel["title"] == "edge: två räta linjer" and len(panel["lines"][1][0]) == 3


def test_performance_panel_after_perf(tmp_path, capsys):
    """performance: tiden för läs och räkna per mätning ur perf; median och bilder/s i tabellen."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "perf 5")
    panel = display.panel(state, "performance", None, None)
    assert [len(line[0]) for line in panel["lines"]] == [5, 5]
    assert panel["text"].splitlines()[0].startswith("läs median ") and panel["text"].endswith(" bilder/s")


def test_every_panel_draws_in_the_window(tmp_path, capsys):
    """view analysis NAMN för varje ny panel: fönstret (Agg) ritar panelen med rubrik, kurvor och lika skala i xy."""
    state = glow_lamp()
    registry.run_command(state, "color")
    registry.run_command(state, f"mix {rgb(tmp_path)} --sweep")
    edge = transmission_state(edge_at(550))
    registry.run_command(edge, "bandgap")
    state["view"]["results"]["edge"] = edge["view"]["results"]["edge"]
    for name in ("colour", "rgb", "edge"):
        registry.run_command(state, f"view analysis {name}")
        spectrum = state["spectrum"]
        values = np.where(spectrum["mask"], spectrum["values"], np.nan)
        win = plot.open_plot()
        try:
            win.update(display.window_info(state))
            win.update(display.frame_info(state, win, spectrum, values))
            display.draw_spectrum(state, win, spectrum, values)
            assert win["panel_ax"].get_title(loc="left") == win["panel"]["title"]
            assert len(win["panel_ax"].lines) == len(win["panel"]["lines"]) + 1
            assert (win["panel_ax"].get_aspect() == 1.0) == (name != "edge")
        finally:
            plot.close(win)
    assert capsys.readouterr().out.splitlines()[-1] == "view analysis: edge"
