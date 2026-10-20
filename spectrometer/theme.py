"""Fönstrets färger, light och dark. plot.py anropar apply(); ingen annan modul vet om färger."""

THEMES = {
    "light": {"bg": "#ffffff", "axes": "#ffffff", "fg": "#18211c", "grid": "#d6dbd6", "line": "#1f66b0", "ref": "#b5470f", "warn": "#c2341f"},
    "dark": {"bg": "#111827", "axes": "#1f2937", "fg": "#e5e7eb", "grid": "#374151", "line": "#22d3ee", "ref": "#f59e0b", "warn": "#f87171"},
}


def apply(fig, ax, name="dark"):
    """Sätt temat på figuren och axlarna; ger färgerna så att plot.py kan färga kurvorna."""
    t = THEMES[name]
    fig.set_facecolor(t["bg"])
    ax.set_facecolor(t["axes"])
    ax.tick_params(colors=t["fg"])
    for spine in ax.spines.values():
        spine.set_color(t["grid"])
    for label in (ax.xaxis.label, ax.yaxis.label, ax.title):
        label.set_color(t["fg"])
    ax.grid(True, color=t["grid"], linewidth=0.5)
    return t
