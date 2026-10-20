"""Fönstret: öppnar, ritar, väntar och stänger. Räknar inte; den enda modulen i programmet som använder matplotlib."""

import time

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from spectrometer import theme


def open_plot():
    """Öppnar ett fönster med en tom kurva."""
    plt.ion()
    fig, ax = plt.subplots()
    line = ax.plot([], [])[0]
    win = {"fig": fig, "ax": ax, "line": line}
    _setup(win)
    return win


def draw(win, x, values, x_label, y_label, info=None):
    """Byter kurvans värden och ritar om."""
    win["line"].set_data(x, values)
    win["ax"].relim()
    win["ax"].autoscale_view()
    win["ax"].set_xlabel(x_label)
    win["ax"].set_ylabel(y_label)
    _decorate(win, info)
    plt.pause(0.001)


def is_open(win):
    """Sant så länge fönstret inte är stängt."""
    return plt.fignum_exists(win["fig"].number)


def pause(seconds):
    """Låter fönstret rita och ta emot klick en stund."""
    plt.pause(seconds)


def close(win):
    """Stänger fönstret."""
    plt.close(win["fig"])


def show():
    """Visar fönstret tills det stängs."""
    plt.show(block=True)


LABELS = {"pixel": "pixel (läge i bilden)", "signal (counts)": "signal (counts, relativ)"}  # bara visningen


def _setup(win):
    """Nytt fönster: layout som följer fönstrets storlek, mörkt tema, tjockare kurva med namn och 60 % av skärmen."""
    win["fig"].set_layout_engine("constrained")
    win["line"].set_linewidth(1.5)
    win["line"].set_label("senaste mätningen")
    _theme(win)
    _size_window(win["fig"], 0.6)
    _keys(win)


def _size_window(fig, share):
    """Fönstret share av skärmens bredd och höjd (Tk). Agg i testerna och andra backends har inget sådant fönster."""
    try:
        window = fig.canvas.manager.window
        width, height = window.winfo_screenwidth(), window.winfo_screenheight()
        window.geometry(f"{int(width * share)}x{int(height * share)}")
        window.lift()
        window.attributes("-topmost", True)  # fram en gång, sedan som vanligt
        window.attributes("-topmost", False)
    except AttributeError:
        pass


def _theme(win):
    """Temat ur win["view"] (dark om inget sagts), satt bara när det ändrats; ger färgerna."""
    name = win.get("view", {}).get("theme", "dark")
    if win.get("themed") != name:
        win["colors"] = theme.apply(win["fig"], win["ax"], name)
        win["line"].set_color(win["colors"]["line"])
        win["themed"] = name
    return win["colors"]


def _decorate(win, info):
    """Efter kurvan: info (om given) in i win, temat, fönstertiteln och axeltexterna med enhet."""
    if info:
        win.update(info)
    _theme(win)
    if win.get("name") and win.get("named") != win["name"]:
        win["fig"].canvas.manager.set_window_title(win["name"])
        win["named"] = win["name"]
    ax = win["ax"]
    ax.set_xlabel(LABELS.get(ax.get_xlabel(), ax.get_xlabel()))
    ax.set_ylabel(LABELS.get(ax.get_ylabel(), ax.get_ylabel()))
    _live_texts(win)
    _areas(win)
    _camera(win)
    _panel(win)


def _live_texts(win):
    """Det cmd_start lagt i win: rubrik, varning i rött, referens, 100 %-linje, toppmarkör, fast y-skala och fotrad."""
    ax, colors = win["ax"], win["colors"]
    scale = "" if win.get("yscale", "fast") == "fast" else f" · y {win['yscale']}"
    ax.set_title(win.get("title", "") + scale, loc="left", fontsize=9, color=colors["fg"])
    right = "PAUS · p fortsätter" if win.get("paused") else win.get("warn") or ""
    ax.set_title(right, loc="right", fontsize=10, color=colors["warn"], fontweight="bold")
    _extra(win, "ref", "-", colors["ref"], "referens")
    _extra(win, "guide", ":", colors["fg"], "_100 %")
    _extra(win, "peak", "v", colors["fg"], "_topp", 2.5)
    _extra(win, "frozen", "--", colors["fg"], win.get("frozen_label", "frusen"))
    _y_scale(win)
    _limits(win)
    _help_text(win)
    _compare(win)
    _legend(win)
    if win.get("foot"):
        win["fig"].supxlabel(win["foot"], fontsize=8, color=colors["fg"])


def _extra(win, key, style, color, label, zorder=1.5):
    """En extra linje win[key + "_line"] med data win[key] = (x, y): skapas första gången, döljs när data saknas.

    zorder 1,5 lägger den under live-kurvan (2), 2,5 ovanpå.
    """
    data = win.get(key)
    artist = win.get(key + "_line")
    if artist is None and data is None:
        return
    if artist is None:
        artist = win[key + "_line"] = win["ax"].plot([], [], style, color=color, lw=1.0, label=label, zorder=zorder)[0]
    artist.set_visible(data is not None)
    if data is not None:
        artist.set_data(*data)
        artist.set_label(label)


def _legend(win):
    """Förklaring bara när fler kurvor än live-kurvan har namn; byggs om bara när namnen ändras."""
    ax, colors = win["ax"], win["colors"]
    names = tuple(line.get_label() for line in ax.lines if line.get_visible() and not line.get_label().startswith("_"))
    if names == win.get("legend"):
        return
    win["legend"] = names
    if len(names) > 1:
        legend = ax.legend(loc="upper right", fontsize=8, facecolor=colors["axes"], edgecolor=colors["grid"])
        for text in legend.get_texts():
            text.set_color(colors["fg"])
    elif ax.get_legend() is not None:
        ax.get_legend().remove()


CAMERA_EVERY = 0.25  # sekunder mellan två kamerabilder i fönstret: begränsat i tid, inte var N:e varv (rev7 L1621)


def _areas(win):
    """Delar fönstret en gång, vid första ritningen: kamera och ROI-remsa överst (1:3), analyspanelen till höger."""
    if "areas" in win:
        return
    view = win.get("view", {})
    top = win.get("image") is not None and (view.get("camera", True) or view.get("roi", True))
    side = win.get("panel") is not None
    win["areas"] = (top, side)
    if not (top or side):
        return
    fig, colors = win["fig"], win["colors"]
    grid = fig.add_gridspec(2 if top else 1, 3, height_ratios=[1, 3] if top else [1])
    row = 1 if top else 0
    win["ax"].set_subplotspec(grid[row, :2] if side else grid[row, :])
    if side:
        win["panel_ax"] = fig.add_subplot(grid[row, 2])
    if not top:
        return
    win["camera_ax"] = fig.add_subplot(grid[0, :2])
    win["strip_ax"] = fig.add_subplot(grid[0, 2])
    for ax, title in ((win["camera_ax"], "kamera"), (win["strip_ax"], "ROI")):
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor(colors["axes"])
        ax.set_title(title, loc="left", fontsize=8, color=colors["fg"])
    win["box_line"] = win["camera_ax"].plot([], [], color=colors["warn"], linewidth=1.0)[0]


def _camera(win):
    """Kamerabilden (nedskalad, BGR till RGB) med ROI-rutan och ROI-remsan, högst var 0,25 s; vyn styr rutorna."""
    view = win.get("view", {})
    image = win.get("image")
    win["ax"].set_visible(view.get("spectrum", True))
    if image is None or "camera_ax" not in win:
        return
    now = time.perf_counter()
    if now - win.get("camera_time", -CAMERA_EVERY) < CAMERA_EVERY:
        return
    win["camera_time"] = now
    x, y, w, h = win["roi"]
    step = max(1, image.shape[1] // 320)  # högst ca 320 kolumner i fönstret
    _show_image(win, "camera", image[::step, ::step, ::-1], (0, image.shape[1], image.shape[0], 0))
    win["box_line"].set_data([x, x + w, x + w, x, x], [y, y, y + h, y + h, y])
    strip = image[y:y + h, x:x + w, ::-1]
    if win.get("axis") == "vertical":
        strip = strip.transpose(1, 0, 2)  # remsan med spektrumet åt höger även vid vertical
    _show_image(win, "strip", strip, None)
    win["camera_ax"].set_visible(view.get("camera", True))
    win["strip_ax"].set_visible(view.get("roi", True))


def _show_image(win, key, rgb, extent):
    """Bilden i rutan win[key + "_ax"]: imshow första gången, sedan bara nya pixlar (set_data)."""
    if key + "_image" not in win:
        aspect = "auto" if extent is None else "equal"
        win[key + "_image"] = win[key + "_ax"].imshow(rgb, extent=extent, aspect=aspect, interpolation="nearest")
    else:
        win[key + "_image"].set_data(rgb)


def _keys(win):
    """Tangentkön: varje tangent i fönstret hamnar i win["keys"], som start läser. Matplotlibs egna tangenter stängs av."""
    for name in [key for key in plt.rcParams if key.startswith("keymap.")]:
        plt.rcParams[name] = []
    win["keys"] = []
    win["fig"].canvas.mpl_connect("key_press_event", lambda event: win["keys"].append(event.key))


def _y_scale(win):
    """y-skalan efter tangenten y: fast (per storhet, standard), auto, eller zoom (senaste kurvan plus 10 %)."""
    scale = win.get("yscale", "fast")
    if scale == "fast" and win.get("fixed_y") is not None:
        win["ax"].set_ylim(*win["fixed_y"])
    elif scale == "zoom":
        y = np.asarray(win["line"].get_ydata(), dtype=float)
        y = y[np.isfinite(y)]
        if y.size and y.max() > y.min():
            pad = 0.1 * (y.max() - y.min())
            win["ax"].set_ylim(y.min() - pad, y.max() + pad)


def _help_text(win):
    """Tangenthjälpen (h) som en ruta uppe till vänster i diagrammet; tom text döljer den."""
    text = win.get("help") or ""
    if "help_text" not in win:
        if not text:
            return
        ax, colors = win["ax"], win["colors"]
        box = {"facecolor": colors["bg"], "edgecolor": colors["grid"]}
        win["help_text"] = ax.text(0.01, 0.97, "", transform=ax.transAxes, va="top", fontsize=8, color=colors["fg"], bbox=box)
    win["help_text"].set_text(text)
    win["help_text"].set_visible(bool(text))


def save_png(path, x, values, x_label, y_label, title=""):
    """Rapportfigur som PNG utan fönster (Figure och FigureCanvasAgg, inte pyplot): ljust tema, 200 dpi, topp markerad.

    Går utan skärm och i testerna; values har NaN där mätningen är ogiltig (luckor i kurvan).
    """
    fig = Figure(figsize=(8, 4.5), layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    colors = theme.apply(fig, ax, "light")
    ax.plot(x, values, color=colors["line"], linewidth=1.5)
    if np.any(np.isfinite(values)):
        i = int(np.nanargmax(values))
        ax.plot([x[i]], [values[i]], "v", color=colors["warn"])
        ax.annotate(f"{x[i]:g}", (x[i], values[i]), textcoords="offset points", xytext=(5, 5), fontsize=8, color=colors["fg"])
    ax.set_xlabel(LABELS.get(x_label, x_label))
    ax.set_ylabel(LABELS.get(y_label, y_label))
    ax.set_title(title, loc="left", fontsize=8, color=colors["fg"])
    fig.savefig(path, dpi=200)


PANEL_EVERY = 0.5  # sekunder mellan två omritningar av analyspanelen


def _panel(win):
    """Analyspanelen till höger om spektrumet ur win["panel"]: kurvor, punkter och en kort tabell; högst var 0,5 s."""
    panel = win.get("panel")
    if panel is None or "panel_ax" not in win:
        return
    now = time.perf_counter()
    if now - win.get("panel_time", -PANEL_EVERY) < PANEL_EVERY:
        return
    win["panel_time"] = now
    ax, colors = win["panel_ax"], win["colors"]
    ax.cla()
    theme.apply(win["fig"], ax, win["themed"])
    ax.tick_params(labelsize=7)
    ax.set_title(panel["title"], loc="left", fontsize=8, color=colors["fg"])
    for (x, y, label), color in zip(panel["lines"], (colors["line"], colors["ref"], colors["fg"])):
        ax.plot(x, y, color=color, linewidth=1.0, label=label)
    if panel["points"] is not None:
        ax.plot(*panel["points"], "v", color=colors["warn"])
    ax.set_xlabel(panel["x_label"], fontsize=7, color=colors["fg"])
    ax.text(0.02, 0.97, panel["text"], transform=ax.transAxes, va="top", fontsize=7, family="monospace",
            color=colors["fg"])


def _compare(win):
    """Jämförelsekurvorna (view compare add) som tunna linjer med egen stil och etikett; skapas en gång per fönster."""
    if "compare_lines" in win:
        return
    styles = ("-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)))
    win["compare_lines"] = [
        win["ax"].plot(x, y, linestyle=styles[i % len(styles)], color=win["colors"]["fg"], linewidth=1.0, alpha=0.8,
                       label=label, zorder=1.5)[0]
        for i, (x, y, label) in enumerate(win.get("compare", []))
    ]


def _limits(win):
    """view xlim och view ylim: gränser som du satt vid prompten går före y-tangenten och den fasta skalan."""
    view = win.get("view", {})
    if view.get("xlim"):
        win["ax"].set_xlim(*view["xlim"])
    if view.get("ylim"):
        win["ax"].set_ylim(*view["ylim"])


STYLES = ("-", "--", "-.", ":")  # linjestilar: kurvorna går att skilja åt också i svartvitt
PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000")  # Okabe-Ito, färgblindsäker


def _spectra(fig, curves, x_label, y_label):
    """Kurvorna [(x, y, namn)] i en ny axel i fig: ljust tema, egen färg och linjestil per kurva, legend. Ger axeln."""
    ax = fig.add_subplot()
    theme.apply(fig, ax, "light")
    for k, (x, y, name) in enumerate(curves):
        marker = "o" if len(x) <= 30 else None  # 1.2.6: serier har få punkter, och de ska synas
        ax.plot(x, y, linestyle=STYLES[k % len(STYLES)], color=PALETTE[k % len(PALETTE)], linewidth=1.2, label=name,
                marker=marker, markersize=4)
    ax.set_xlabel(LABELS.get(x_label, x_label))
    ax.set_ylabel(LABELS.get(y_label, y_label))
    ax.legend(fontsize=8)
    return ax


def show_spectra(curves, x_label, y_label):
    """compare: kurvorna i ett fönster som väntar tills det stängs; fönstret stängs alltid efteråt."""
    fig = plt.figure(layout="constrained")
    try:
        _spectra(fig, curves, x_label, y_label)
        show()
    finally:
        plt.close(fig)


def save_figure(path, curves, x_label, y_label, xlim=None, log=False):
    """figure: rapportfigur utan fönster (Figure, inte pyplot): 16 x 9 cm, 200 dpi, ingen titel; PNG eller SVG efter ändelsen.

    Legend bara när kurvorna är fler än en. xlim: (min, max) eller None; log: logaritmisk y-axel.
    """
    fig = Figure(figsize=(16 / 2.54, 9 / 2.54), layout="constrained")
    FigureCanvasAgg(fig)
    ax = _spectra(fig, curves, x_label, y_label)
    if len(curves) == 1:
        ax.get_legend().remove()
    if xlim is not None:
        ax.set_xlim(*xlim)
    if log:
        ax.set_yscale("log")
    fig.savefig(path, dpi=200)
