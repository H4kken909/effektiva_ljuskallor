DARK = {
    "bg": "#07060b", "axes": "#07060b", "pane": "#0d0a14", "bg_dark": "#130f1c", "hair": "#231a33",
    "grid": "#181224", "grid_style": (0, (1, 3)), "grid_width": 0.72, "grid_alpha": 1.0, "camera_bg": "#07060b",
    "select": "#2c1f45",
    "fg": "#e9e1f5", "cmd": "#e9e1f5", "text": "#a99bc0", "value": "#c9bddb", "dim": "#6e5f86",
    "comment": "#6e5f86", "label": "#8d7ea6", "gutter": "#4a3d5e", "faint": "#4a3d5e",
    "pink": "#ff2fa8", "hot": "#ff5ccf", "purple": "#9d6bff", "violet": "#c4a1ff", "star": "#7aa8ff",
    "mint": "#5ff2b0", "amber": "#ffb454", "red": "#ff4d5e",
    "line": "#c4a1ff", "curve": "#d9c2ff", "peak": "#ff2fa8", "fill": "#9d6bff", "roi": "#9d6bff",
    "ref": "#7aa8ff", "warn": "#ff4d5e", "prompt": "#ff2fa8", "blue": "#7aa8ff",
    "yellow": "#ffe14d", "green": "#5ff2b0", "teal": "#5ff2b0", "ok": "#5ff2b0",
}

REPORT = {"bg": "#ffffff", "axes": "#ffffff", "fg": "#18211c", "grid": "#d6dbd6", "dim": "#5f6b64", "line": "#1f66b0",
          "ref": "#b5470f", "warn": "#c2341f", "grid_style": "-", "grid_width": 0.6, "grid_alpha": 0.7}

GLOW = (("#ff2fa8", 30, 0.085), ("#ff5ccf", 16, 0.11), ("#9d6bff", 8, 0.24), ("#c4a1ff", 3, 0.55))
GLOW_LEVELS = ("on", "low", "off")
SKY = ("#07060b", "#140d22")
FILL_ALPHA = 0.07

MONO_FONTS = ("JetBrains Mono", "JetBrainsMono NFM", "JetBrainsMono Nerd Font Mono", "JetBrainsMono Nerd Font",
              "Consolas", "DejaVu Sans Mono")


def glow(level="on"):
    return {"off": (), "low": GLOW[2:]}.get(level, GLOW)


def apply(fig, ax, t):
    fig.set_facecolor(t["bg"])
    ax.set_facecolor(t["axes"])
    ax.tick_params(colors=t["dim"], labelcolor=t["fg"], labelsize=10)
    for side, spine in ax.spines.items():
        spine.set_color(t["grid"])
        spine.set_visible(side in ("left", "bottom"))
    for label in (ax.xaxis.label, ax.yaxis.label, ax.title):
        label.set_color(t["fg"])
    ax.xaxis.label.set_size(11)
    ax.yaxis.label.set_size(11)
    ax.grid(True, color=t["grid"], linewidth=t["grid_width"], alpha=t["grid_alpha"], linestyle=t["grid_style"])
    ax.set_axisbelow(True)
    return t
