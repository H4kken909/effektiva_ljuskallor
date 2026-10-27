import time

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_hex, to_rgb
from matplotlib.figure import Figure
from matplotlib.font_manager import fontManager
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import Bbox, blended_transform_factory, offset_copy

from spectrometer.visual import raster, theme

PX = 0.72
LABEL_ABOVE = 24
LABELS = {"pixel": "pixel (position in the image)", "signal (counts)": "signal (counts, relative)"}
PALETTE = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000")
CAMERA_PARTS = {"camera_ax": ("camera_image", "box_line", "camera_text", "roi_text"),
                "strip_ax": ("strip_image", "strip_text")}


def open_plot():
    plt.ion()
    plt.rcParams["toolbar"] = "None"
    for name in [key for key in plt.rcParams if key.startswith("keymap.")]:
        plt.rcParams[name] = []
    fig, ax = plt.subplots(figsize=(12, 6.75), layout="constrained")
    line = ax.plot([], [], linewidth=1.6, solid_joinstyle="round", label="latest measurement", zorder=2)[0]
    fill = ax.fill_between([], [], 0, linewidth=0, alpha=0.10, label="_ytan", zorder=1.8)
    ax.set_xmargin(0)
    colors = theme.apply(fig, ax, theme.DARK)
    line.set_color(colors["line"])
    fill.set_color(colors["line"])
    text = ax.annotate("", (0, 0), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9,
                       color=colors["fg"], fontweight="bold", zorder=2.5, annotation_clip=True)
    try:
        window = fig.canvas.manager.window
        width, height = window.winfo_screenwidth(), window.winfo_screenheight()
        window.geometry(f"{int(width * 0.75)}x{int(height * 0.75)}+{int(width * 0.125)}+{int(height * 0.0625)}")
        window.lift()
        window.attributes("-topmost", True)
        window.attributes("-topmost", False)
    except AttributeError:
        pass
    return {"fig": fig, "ax": ax, "line": line, "fill": fill, "colors": colors, "peak_text": text}


def embed(master):
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    fig = Figure(figsize=(9, 6), dpi=100)
    canvas = FigureCanvasTkAgg(fig, master=master)
    ax = fig.add_axes((0.1, 0.1, 0.8, 0.8))
    fonts = {entry.name for entry in fontManager.ttflist}
    mono = next((name for name in theme.MONO_FONTS if name in fonts), "DejaVu Sans Mono")
    sans = "Inter" if "Inter" in fonts else "DejaVu Sans"
    colors = theme.apply(fig, ax, theme.DARK)
    line = ax.plot([], [], linewidth=1.5 * PX, solid_joinstyle="round", solid_capstyle="round",
                   label="latest measurement", zorder=2, color=colors["curve"])[0]
    cam = fig.add_axes((0, 0, 0.1, 0.1), sharex=ax)
    strip = fig.add_axes((0, 0, 0.1, 0.1), sharex=ax)
    cam.set_autoscale_on(False)
    strip.set_autoscale_on(False)
    strip.set_ylim(0, 1)
    sky = _Sky(ax)
    sky.set_zorder(0.1)
    ax.add_artist(sky)
    ax.set_xmargin(0)
    box = {"boxstyle": "square,pad=0.2", "linewidth": 0, "alpha": 0.7, "facecolor": colors["bg_dark"]}
    win = {"fig": fig, "ax": ax, "line": line, "widget": canvas.get_tk_widget(), "rows": (), "colors": colors,
           "mono": mono, "sans": sans, "view": {"glow": "on", "spectrum": True, "camera_view": "crop"},
           "peak": None, "image": None, "px": None, "x": None, "hot_band": None, "fixed_y": None, "sat_level": None,
           "camera_ax": cam, "strip_ax": strip, "camera_image": _Pixels(cam), "strip_image": _Pixels(strip),
           "box_line": cam.plot([], [], linewidth=PX, antialiased=False, color=colors["roi"], alpha=0.75)[0],
           "camera_text": _Stamp(cam, (0, 1), cam.transAxes, (6, -5), "left", "top", fontsize=8, family=mono,
                                 bbox=box, color=colors["label"]),
           "roi_text": _Stamp(cam, (1, 0), blended_transform_factory(cam.transAxes, cam.transData), (-6, 0), "right",
                              "center", fontsize=8, family=mono, fontweight="bold", alpha=0.85, color=colors["violet"]),
           "strip_text": _Stamp(strip, (0, 0.5), strip.transAxes, (6, 0), "left", "center", fontsize=8, family=mono,
                                alpha=0.55, color=colors["fg"]),
           "peak_text": _Stamp(ax, (0, 0), ax.transData, (0, LABEL_ABOVE), "center", "center", fontsize=9,
                               family=mono, fontweight="bold", color=colors["peak"],
                               bbox={"boxstyle": "round,pad=0.45,rounding_size=0.3", "facecolor": colors["bg_dark"],
                                     "edgecolor": colors["peak"], "linewidth": PX}),
           "peak_line": ax.plot([], [], "o", label="_topp", zorder=2.6, animated=True)[0],
           "peak_leader": ax.plot([], [], label="_ledlinje", zorder=2.9, animated=True)[0],
           "unit_text": ax.annotate("", (1, 0), xycoords="axes fraction", xytext=(-6, -10), textcoords="offset points",
                                    ha="right", va="center", fontsize=8, family=sans, annotation_clip=False,
                                    color=colors["gutter"]),
           "hairline": fig.add_artist(Line2D([0, 1], [0, 0], transform=fig.transFigure, antialiased=False,
                                             solid_capstyle="butt", color=colors["hair"]))}
    win["roi_text"].text = "◀ ROI"
    win["strip_text"].text = "ROI mean"
    _window_style(win)
    canvas.mpl_connect("resize_event", lambda event: place(win, win["rows"]))
    return win


class _Pixels(Artist):
    def __init__(self, ax):
        super().__init__()
        self.ax = ax
        self.rgba = None
        self.set_figure(ax.figure)

    def size(self):
        box = self.ax.bbox
        return max(1, round(box.x1) - round(box.x0)), max(1, round(box.y1) - round(box.y0))

    def draw(self, renderer):
        if self.rgba is None or not self.get_visible():
            return
        box = self.ax.bbox
        gc = renderer.new_gc()
        gc.set_clip_rectangle(box)
        renderer.draw_image(gc, round(box.x0), round(box.y0), self.rgba)
        gc.restore()


class _Sky(_Pixels):
    def draw(self, renderer):
        width, height = self.size()
        if self.rgba is None or self.rgba.shape[:2] != (height, width):
            top, bottom = (np.array(to_rgb(colour)) for colour in theme.SKY)
            rows = np.rint(255 * (top + (bottom - top) * np.linspace(1.0, 0.0, height)[:, None] ** 2.2))
            self.rgba = np.empty((height, width, 4), np.uint8)
            self.rgba[..., :3] = rows.astype(np.uint8)[:, None, :]
            self.rgba[..., 3] = 255
        super().draw(renderer)


class _Stamp(Artist):
    def __init__(self, ax, xy, transform, offset, ha, va, **props):
        super().__init__()
        self.xy, self.transform, self.offset, self.ha, self.va, self.props = xy, transform, offset, ha, va, props
        self.text = ""
        self.rgba = None
        self.key = None
        self.set_figure(ax.figure)

    def place(self):
        if not self.text or not self.get_visible():
            return None
        dpi = self.figure.dpi
        if self.key != (self.text, dpi):
            self.rgba = _text_image(self.text, self.props, dpi)
            self.key = (self.text, dpi)
        x, y = self.transform.transform(self.xy)
        if not np.isfinite(x + y):
            return None
        h, w = self.rgba.shape[:2]
        x += self.offset[0] * dpi / 72 - {"left": 0, "center": w / 2, "right": w}[self.ha]
        y += self.offset[1] * dpi / 72 - {"bottom": 0, "center": h / 2, "top": h}[self.va]
        return round(x), round(y)

    def draw(self, renderer):
        where = self.place()
        if where is None:
            return
        gc = renderer.new_gc()
        gc.set_clip_rectangle(self.figure.bbox)
        renderer.draw_image(gc, *where, self.rgba)
        gc.restore()


def _text_image(text, props, dpi):
    fig = Figure(figsize=(1, 1), dpi=dpi)
    canvas = FigureCanvasAgg(fig)
    fig.patch.set_alpha(0)
    pad = 4 * dpi / 72 + (3 * props["fontsize"] * dpi / 72 if "bbox" in props else 0)
    artist = fig.text(0, 0, text, ha="left", va="bottom", transform=None, **props)
    extent = artist.get_window_extent(canvas.get_renderer())
    fig.set_size_inches((extent.width + 2 * pad) / dpi, (extent.height + 2 * pad) / dpi)
    artist.set_position((pad, pad))
    canvas.draw()
    renderer = canvas.get_renderer()
    boxes = [artist.get_window_extent(renderer)]
    if artist.get_bbox_patch() is not None:
        boxes.append(artist.get_bbox_patch().get_window_extent(renderer))
    box = Bbox.union(boxes)
    pixels = np.asarray(canvas.buffer_rgba())
    height = pixels.shape[0]
    top, bottom = max(0, int(np.floor(height - box.y1)) - 1), min(height, int(np.ceil(height - box.y0)) + 1)
    left, right = max(0, int(np.floor(box.x0)) - 1), min(pixels.shape[1], int(np.ceil(box.x1)) + 1)
    return np.ascontiguousarray(pixels[top:bottom, left:right][::-1])


def _peak_glow(k, colors):
    size = int(round(120 * k)) // 2 * 2
    r = np.arange(size) + 0.5 - size / 2
    dist = r[:, None] ** 2 + r[None, :] ** 2
    halo = 0.42 * np.exp(-dist / (2 * (20 * k) ** 2))
    core = 0.90 * np.exp(-dist / (2 * (4 * k) ** 2))
    alpha = core + halo * (1 - core)
    rgb = (core[..., None] * to_rgb(colors["hot"]) + (halo * (1 - core))[..., None] * to_rgb(colors["peak"])) \
        / np.maximum(alpha, 1e-6)[..., None]
    rgba = np.empty((size, size, 4), np.uint8)
    rgba[..., :3] = np.clip(np.rint(rgb * 255), 0, 255)
    rgba[..., 3] = np.clip(np.rint(alpha * 255), 0, 255)
    return rgba


def place(win, rows):
    win["rows"] = tuple(rows)
    fig = win["fig"]
    height = fig.get_size_inches()[1] * fig.dpi
    k = fig.dpi / 100
    hair = max(1, round(k))
    full = win["view"]["camera_view"] == "full"
    win["placed_full"] = full
    axes = {"camera": win["camera_ax"], "strip": win["strip_ax"], "curve": win["ax"]}
    share = {"camera": 2.6 if full else 1.0, "curve": 5.6}
    seam = "curve" in rows and rows[0] != "curve"
    spare = max(0.0, height - k * (20 * ("strip" in rows) + 28 * ("curve" in rows)) - hair * seam)
    weights = sum(share[name] for name in rows if name != "strip")
    y = float(round(height))
    for name, ax in axes.items():
        ax.set_visible(name in rows)
    for name in rows:
        if name == "curve" and seam:
            y -= hair
            win["hairline"].set_ydata([(y + hair / 2) / height] * 2)
            win["hairline"].set_linewidth(hair * 72 / fig.dpi)
        tall = k * 20 if name == "strip" else spare * share[name] / weights
        low = max(0.0, float(round(y - tall)))
        axes[name].set_position((0.0, low / height, 1.0, max(y - low, 1.0) / height))
        y = low - (round(k * 28) if name == "curve" else 0)
    win["hairline"].set_visible(seam)
    win.pop("bg", None)


def draw(win, x, values, x_label, y_label):
    ax, colors = win["ax"], win["colors"]
    win["line"].set_data(x, values)
    win["fill"].set_data(x, values, 0)
    ax.relim()
    ax.autoscale_view()
    ax.set_xlabel(LABELS.get(x_label, x_label))
    ax.set_ylabel(LABELS.get(y_label, y_label))
    win["fig"].canvas.manager.set_window_title(win["name"])
    ax.set_title(win["title"], loc="left", fontsize=11, color=colors["fg"], linespacing=1.5)
    badge = ax.set_title(win["warn"] or "", loc="right", fontsize=11, color=colors["bg"], fontweight="bold")
    badge.set_bbox({"boxstyle": "round,pad=0.35", "facecolor": colors["warn"], "edgecolor": "none"})
    _extra(win, "ref", "-", colors["ref"], "reference")
    _extra(win, "guide", ":", colors["fg"], "_100 %")
    _extra(win, "peak", "v", colors["fg"], "_topp", 2.5)
    peak = win["peak"]
    win["peak_text"].set_visible(peak is not None)
    if peak is not None:
        win["peak_text"].xy = (peak[0][0], peak[1][0])
        win["peak_text"].set_text(f"{peak[1][0]:.4g}  @ {peak[0][0]:.4g}")
    if win["fixed_y"] is not None:
        ax.set_ylim(*win["fixed_y"])
    _curve_legend(win)
    if win["foot"]:
        win["fig"].supxlabel(win["foot"], fontsize=9, color=colors["dim"])
    ax.set_visible(win["view"]["spectrum"])
    plt.pause(0.001)


def _update(win, x, values, x_label):
    win["x"] = x
    win["line"].set_data(x, values)
    ax, colors = win["ax"], win["colors"]
    ax.relim()
    ax.autoscale_view()
    _extra(win, "ref", "-", colors["ref"], "reference")
    _extra(win, "guide", ":", colors["fg"], "_100 %")
    _peak(win)
    if win["fixed_y"] is not None:
        ax.set_ylim(*win["fixed_y"])
    _curve_legend(win)
    ax.set_visible(win["view"]["spectrum"])
    _camera_frame(win)
    _marks(win)
    win["unit_text"].set_text({"pixel": "pixel", "wavelength (nm)": "nm"}.get(x_label, x_label))


def draw_live(win, x, values, x_label, y_label, full):
    span = (len(x), float(x[0]), float(x[-1]), x_label, y_label) if len(x) else None
    if full or win.get("bg") is None or span != win.get("span") or win["fixed_y"] is None:
        _update(win, x, values, x_label)
        win["span"] = span
        win["fig"].canvas.draw_idle()
        return "full"
    win["x"] = x
    win["line"].set_data(x, values)
    _peak(win)
    canvas = win["fig"].canvas
    if win["ax"].get_visible():
        _paint(win)
        canvas.blit(win["ax"].bbox)
    if _camera_frame(win):
        canvas.blit(_draw_camera(win))
    return "fast"


def _draw_camera(win):
    boxes = []
    for key, names in CAMERA_PARTS.items():
        if win[key].get_visible():
            for name in names:
                win["fig"].draw_artist(win[name])
            boxes.append(win[key].bbox)
    return Bbox.union(boxes) if boxes else None


def enable_blit(win):
    win["line"].set_animated(True)
    win["peak_text"].set_animated(True)
    win["fig"].canvas.mpl_connect("draw_event", lambda event: _on_draw(win))


def _on_draw(win):
    pixels = np.asarray(win["fig"].canvas.buffer_rgba())
    fig_height, fig_width = pixels.shape[:2]
    box = win["ax"].bbox
    x0, x1 = max(0, round(box.x0)), min(fig_width, round(box.x1))
    top, bottom = max(0, fig_height - round(box.y1)), min(fig_height, fig_height - round(box.y0))
    width, height = max(0, x1 - x0), max(0, bottom - top)
    win["region"] = (x0, top, width, height, fig_height)
    win["bg_px"] = pixels[top:top + height, x0:x0 + width].copy()
    win["bg"] = True
    if win["ax"].get_visible():
        _paint(win)
    _draw_camera(win)


def _paint(win):
    x0, top, width, height, fig_height = win["region"]
    frame = np.asarray(win["fig"].canvas.buffer_rgba())[top:top + height, x0:x0 + width]
    colors, dpi = win["colors"], win["fig"].dpi
    k = dpi / 100
    origin = (x0, fig_height - top)
    to_screen = win["ax"].transData.get_affine().get_matrix()

    def at(xy):
        px, py = to_screen[:2] @ (xy[0], xy[1], 1.0)
        return px - origin[0] - 0.5, origin[1] - py - 0.5

    x, y = (np.asarray(data, dtype=float) for data in win["line"].get_data())
    lines = []
    if len(x):
        points = np.column_stack([x, y]) @ to_screen[:2, :2].T + to_screen[:2, 2]
        lines = raster.runs(points, (width, height), origin)
    strokes = [(colour, size * k, alpha) for colour, size, alpha in theme.glow(win["view"]["glow"])]
    look = raster.look(colors["axes"], to_hex(win["line"].get_color()), strokes, colors["fill"], theme.FILL_ALPHA)
    raster.glow(frame, win["bg_px"], lines, at((0.0, 0.0))[1], look)
    peak = win["peak"]
    if peak is not None:
        tip = at((peak[0][0], peak[1][0]))
        sprite = _peak_glow(k, colors)
        raster.stamp(frame, sprite, (round(tip[0] + 0.5 - sprite.shape[1] / 2), round(tip[1] + 0.5 - sprite.shape[0] / 2)))
    raster.curve(frame, lines, look, k)
    band = win["hot_band"]
    if band is not None and lines:
        rows = origin[1] - (np.arange(height) + 0.5)
        ramp = np.clip(((rows - to_screen[1, 2]) / to_screen[1, 1] - band[0]) / (band[1] - band[0]), 0.0, 1.0)
        ramp = ramp * ramp * (3 - 2 * ramp)
        raster.hot(frame, lines, ramp, [255.0 * v for v in to_rgb(colors["amber"])], 0.30)
    leader = win["peak_leader"]
    if leader.get_visible() and len(leader.get_xdata()) == 2:
        alpha = 0.7
        mixed = [255.0 * (alpha * a + (1 - alpha) * b) for a, b in zip(to_rgb(colors["peak"]), to_rgb(colors["axes"]))]
        raster.line(frame, *(at(xy) for xy in zip(leader.get_xdata(), leader.get_ydata())), tuple(mixed))
    if peak is not None:
        raster.ring(frame, tip, 6 * PX * dpi / 144, 1.2 * PX * dpi / 72, tuple(255.0 * v for v in to_rgb(colors["bg"])),
                    tuple(255.0 * v for v in to_rgb(colors["peak"])))
        where = win["peak_text"].place()
        if where is not None:
            text = win["peak_text"]
            raster.stamp(frame, text.rgba, (where[0] - origin[0], origin[1] - where[1] - text.rgba.shape[0]))


def is_open(win):
    return plt.fignum_exists(win["fig"].number)


def pause(seconds):
    plt.pause(seconds)


def close(win):
    plt.close(win["fig"])


def show():
    plt.show(block=True)


def _window_style(win):
    ax, colors = win["ax"], win["colors"]
    for side, spine in ax.spines.items():
        spine.set_visible(side == "bottom")
        spine.set_color(colors["gutter"])
        spine.set_linewidth(PX)
    ax.tick_params(axis="x", direction="out", length=4, width=PX, color=colors["gutter"], labelcolor=colors["comment"],
                   labelsize=8.5, labelfontfamily=win["sans"], pad=3)
    ax.tick_params(axis="y", left=False, labelleft=False)
    ax.xaxis.grid(False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, pos: _tick_text(ax, value)))
    for small in (win["camera_ax"], win["strip_ax"]):
        small.set_facecolor(colors["camera_bg"])
        small.axis("off")


def _tick_text(ax, value):
    low, high = sorted(ax.get_xlim())
    if high > low and min(value - low, high - value) < 0.02 * (high - low):
        return ""
    return f"{value:g}"


def _peak(win):
    text, leader, ax = win["peak_text"], win["peak_leader"], win["ax"]
    found = win["peak"] is not None
    text.set_visible(found)
    leader.set_visible(found)
    if not found:
        return
    win["peak_line"].set_data(*win["peak"])
    (x,), (y,) = win["peak"]
    text.xy = (x, y)
    label = win["peak_label"]
    if _due(win, "readout_time", 0.25) or not text.text:
        text.text = label
    k = win["fig"].dpi / 100
    tip_x, tip_y = ax.transData.transform((x, y))
    box = ax.bbox
    half = 0.5 * len(label) * 7.5 * k + 10 * k
    if box.y1 - tip_y > (LABEL_ABOVE + 14) / PX * k:
        dx = 0.0
        if tip_x - half < box.x0 + 4 * k:
            dx = (box.x0 + 4 * k + half - tip_x) * PX / k
        elif tip_x + half > box.x1 - 4 * k:
            dx = -(tip_x + half - box.x1 + 4 * k) * PX / k
        text.offset, text.ha = (dx, LABEL_ABOVE), "center"
        back = ax.transData.inverted()
        leader.set_data([x, x], [back.transform((tip_x, tip_y + 4 * k))[1],
                                 back.transform((tip_x, tip_y + (LABEL_ABOVE - 8) / PX * k))[1]])
    else:
        leader.set_data([], [])
        text.offset, text.ha = ((14, -6), "left") if tip_x + 2 * half + 30 * k < box.x1 else ((-14, -6), "right")


def _marks(win):
    ax, colors = win["ax"], win["colors"]
    for artist in win.get("marks", []):
        artist.remove()
    win["marks"] = marks = []
    level = win["sat_level"]
    low, high = sorted(ax.get_ylim())
    if level is not None and low < level < high:
        marks.append(ax.axhspan(level * 240 / 255, level, facecolor=colors["amber"], alpha=0.04, linewidth=0,
                                zorder=0.5))
        marks.append(ax.axhline(level, color=colors["amber"], alpha=0.5, linewidth=PX, linestyle=(0, (3, 3)),
                                zorder=1.2, label="_saturation"))
        marks.append(ax.annotate(f"{level:g} · saturation", (1, level), xycoords=("axes fraction", "data"),
                                 xytext=(-6, 3), textcoords="offset points", ha="right", va="bottom", fontsize=8,
                                 family=win["sans"], color=colors["amber"], alpha=0.7, annotation_clip=False))
    span = (high - low) / max(1.0, ax.bbox.height) * win["fig"].dpi / 72
    transform = offset_copy(blended_transform_factory(ax.transAxes, ax.transData), win["fig"], 6, 0, units="points")
    for tick in ax.yaxis.get_major_locator().tick_values(low, high):
        if low < tick < high and tick != 0:
            under = level is not None and 0 <= level - tick < 16 * span
            marks.append(ax.text(0, tick - 2 * span if under else tick + 2 * span, f"{tick:g}",
                                 transform=transform, fontsize=8, family=win["sans"], ha="left", zorder=1.1,
                                 color=colors["comment"], va="top" if under else "bottom"))


def _extra(win, key, style, color, label, zorder=1.5):
    data = win.get(key)
    line = win.get(key + "_line")
    if line is None and data is None:
        return
    if line is None:
        line = win[key + "_line"] = win["ax"].plot([], [], style, color=color, lw=1.0, label=label, zorder=zorder)[0]
    line.set_visible(data is not None)
    if data is not None:
        line.set_data(*data)


def _curve_legend(win):
    ax = win["ax"]
    names = [line for line in ax.lines if line.get_visible() and not line.get_label().startswith("_")]
    if ax.get_legend() is not None:
        ax.get_legend().remove()
    if len(names) > 1:
        colors = win["colors"]
        legend = ax.legend(loc="upper right", fontsize=8, facecolor=colors["axes"], edgecolor=colors["grid"])
        for text in legend.get_texts():
            text.set_color(colors["fg"])


def _due(win, key, every):
    now = time.perf_counter()
    if now - win.get(key, -every) < every:
        return False
    win[key] = now
    return True


def _camera_frame(win):
    image, x, px = win["image"], win["x"], win["px"]
    if image is None or not (win["camera_ax"].get_visible() or win["strip_ax"].get_visible()):
        return False
    if not _due(win, "camera_time", win["camera_every"]):
        return False
    if px is None or len(x) < 2 or len(px) != len(x):
        return False
    rx, ry, rw, rh = win["roi"]
    vertical = win["axis"] == "vertical"
    frame = image.transpose(1, 0, 2) if vertical else image
    band, across = (rx, rw) if vertical else (ry, rh)
    cols = np.clip(np.asarray(px, dtype=int), 0, frame.shape[1] - 1)
    width = win["camera_image"].size()[0]
    low, high = win["camera_ax"].get_xlim()
    xs, order = np.asarray(x, dtype=float), np.arange(len(x), dtype=float)
    if xs[-1] < xs[0]:
        xs, order = xs[::-1], order[::-1]
    where = np.interp(low + (np.arange(width) + 0.5) / width * (high - low), xs, order)
    columns = np.clip(np.rint(where).astype(np.intp), 0, len(xs) - 1)
    colours = frame[band:band + across].mean(axis=0)[cols][:, ::-1]
    if colours.max() > 0:
        colours = colours * (255.0 / colours.max())
    fill_pixels(win["strip_image"], np.clip(np.rint(colours), 0, 255).astype(np.uint8)[np.newaxis], columns)
    height = frame.shape[0]
    look = win["camera_look"] if win["view"]["glow"] != "off" else None
    win["roi_text"].xy = (1, band + across / 2)
    if win["view"]["camera_view"] == "full":
        rows = frame[::max(1, height // 240)]
        if look is not None:
            rows = look(rows)
        artist = win["camera_image"]
        shown_width, shown_height = artist.size()
        width = frame.shape[1]
        full_columns = np.minimum(((np.arange(shown_width) + 0.5) * width / shown_width).astype(np.intp), width - 1)
        fill_pixels(artist, rows[..., ::-1], full_columns)
        win["camera_ax"].set_ylim(height, 0)
        win["camera_text"].text = f"camera · full frame {width}×{height}"
        win["box_line"].set_data([], [])
        along, size = (ry, rh) if vertical else (rx, rw)
        left = int(np.clip(round(along * shown_width / width), 0, shown_width - 1))
        right = int(np.clip(round((along + size) * shown_width / width) - 1, left, shown_width - 1))
        upper = int(np.clip(round(band * shown_height / height), 0, shown_height - 1))
        lower = int(np.clip(round((band + across) * shown_height / height) - 1, upper, shown_height - 1))
        colour = np.array([round(255 * v) for v in to_rgb(win["colors"]["roi"])], np.uint8)
        picture = artist.rgba[::-1]
        for edge in (picture[upper, left:right + 1], picture[lower, left:right + 1], picture[upper:lower + 1, left],
                     picture[upper:lower + 1, right]):
            edge[..., :3] = colour
        return True
    margin = max(across // 2, 12)
    top, bottom = (0, height) if across >= height else (max(0, band - margin), min(height, band + across + margin))
    crop = np.take(frame[top:bottom:max(1, (bottom - top) // 240)], cols, axis=1)
    if look is not None:
        crop = look(crop)
    win["camera_ax"].set_ylim(bottom, top)
    win["camera_text"].text = f"camera · rows {top}–{bottom}"
    half = (float(x[-1]) - float(x[0])) / (len(x) - 1) / 2
    left, right = float(x[0]) - half, float(x[-1]) + half
    win["box_line"].set_data([left, right, np.nan, left, right], [band, band, np.nan, band + across, band + across])
    fill_pixels(win["camera_image"], crop[..., ::-1], columns)
    return True


def fill_pixels(artist, image, columns):
    width, height = artist.size()
    packed = np.empty(image.shape[:2] + (4,), dtype=np.uint8)
    packed[..., :3] = image
    packed[..., 3] = 255
    packed = packed.view(np.uint32)[..., 0]
    rows = ((np.arange(height) + 0.5) * image.shape[0] / height).astype(np.intp)[::-1]
    shown = packed[:, columns][rows] if image.shape[0] < height else packed[rows][:, columns]
    if artist.rgba is None or artist.rgba.shape[:2] != (height, width):
        artist.rgba = np.empty((height, width, 4), dtype=np.uint8)
    artist.rgba.view(np.uint32)[..., 0] = shown


def save_png(path, x, values, x_label, y_label, title):
    fig = Figure(figsize=(8, 4.5), layout="constrained")
    ax = fig.add_subplot()
    colors = theme.apply(fig, ax, theme.REPORT)
    ax.plot(x, values, color=colors["line"], linewidth=1.5)
    if np.any(np.isfinite(values)):
        i = int(np.nanargmax(values))
        ax.plot([x[i]], [values[i]], "v", color=colors["warn"])
        ax.annotate(f"{x[i]:g}", (x[i], values[i]), textcoords="offset points", xytext=(5, 5), fontsize=8,
                    color=colors["fg"])
    ax.set_xlabel(LABELS.get(x_label, x_label))
    ax.set_ylabel(LABELS.get(y_label, y_label))
    ax.set_title(title, loc="left", fontsize=8, color=colors["fg"])
    fig.savefig(path, dpi=200)


def _spectra(fig, curves, x_label, y_label):
    ax = fig.add_subplot()
    theme.apply(fig, ax, theme.REPORT)
    for k, (x, y, name) in enumerate(curves):
        ax.plot(x, y, linestyle=("-", "--", "-.", ":")[k % 4], color=PALETTE[k % len(PALETTE)], linewidth=1.2,
                label=name, marker="o" if len(x) <= 30 else None, markersize=4)
    ax.set_xlabel(LABELS.get(x_label, x_label))
    ax.set_ylabel(LABELS.get(y_label, y_label))
    ax.legend(fontsize=8)
    return ax


def show_spectra(curves, x_label, y_label):
    fig = plt.figure(layout="constrained")
    _spectra(fig, curves, x_label, y_label)
    plt.show(block=True)
    plt.close(fig)


def save_figure(path, curves, x_label, y_label):
    fig = Figure(figsize=(16 / 2.54, 9 / 2.54), layout="constrained")
    ax = _spectra(fig, curves, x_label, y_label)
    if len(curves) == 1:
        ax.get_legend().remove()
    fig.savefig(path, dpi=200)
