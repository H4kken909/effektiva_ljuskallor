"""theme, view och graf: fönstrets färger, vad nästa fönster visar och senaste mätningen i ett fönster.

Terminalen väljer, fönstret visar. Allt här ändrar bara state["view"], aldrig en mätning.
"""

import math
import time

from spectrometer import calc, display, out, plot, registry, theme

GROUP = "mata"  # help.mata visar modulens kommandon

PANES = ("camera", "roi", "spectrum")  # kamerabilden med ROI-rutan, ROI-remsan och spektrumet


@registry.command("theme", "light|dark: fönstrets färger (theme ensam visar valet)", "theme light eller theme dark")
def cmd_theme(state, args):
    """Kommandot theme light eller theme dark: färgerna i nästa fönster (start, graf); theme ensam visar valet."""
    if not args:
        out.say(f"theme: {state['view']['theme']}")
        return
    if len(args) != 1 or args[0] not in theme.THEMES:
        raise ValueError("input.invalid_argument: theme tar ett ord, light eller dark")
    state["view"]["theme"] = args[0]
    out.say(f"theme: {args[0]}")


@registry.command("view", "camera|roi|spectrum|normalize on|off, xlim|ylim MIN MAX|auto, compare add|clear, "
                  "analysis NAMN|off (view ensam visar läget)")
def cmd_view(state, args):
    """Kommandot view: vad nästa fönster (start, graf) visar. Ändrar bara visningen, aldrig en mätning."""
    view = state["view"]
    if not args:
        for name in (*PANES, "normalize"):
            out.say(f"view {name}: {'on' if view[name] else 'off'}")
        for name in ("xlim", "ylim"):
            out.say(f"view {name}: {'auto' if view[name] is None else f'{view[name][0]:g} {view[name][1]:g}'}")
        out.say(f"view compare: {len(view['compare'])} kurvor")
        out.say(f"view analysis: {view['analysis'] or 'off'}")
        return
    what, rest = args[0], args[1:]
    if what in (*PANES, "normalize"):
        if rest not in (["on"], ["off"]):
            raise ValueError(f"input.invalid_argument: view {what} tar on eller off")
        view[what] = rest == ["on"]
        out.say(f"view {what}: {rest[0]}")
    elif what in ("xlim", "ylim"):
        view[what] = _limits(what, rest)
        out.say(f"view {what}: {' '.join(rest)}")
    elif what == "compare":
        _compare(state, rest)
    elif what == "analysis":
        _analysis(state, rest)
    else:
        raise ValueError(f"input.invalid_argument: view {what} finns inte. "
                         "Välj camera, roi, spectrum, normalize, xlim, ylim, compare eller analysis")


def _limits(name, rest):
    """MIN MAX som två ändliga tal i stigande ordning, eller auto (None)."""
    if rest == ["auto"]:
        return None
    registry.need(rest, ("MIN", "MAX"), f"view {name}")
    try:
        low, high = float(rest[0]), float(rest[1])
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: view {name}: MIN och MAX ska vara tal") from error
    if not (math.isfinite(low) and math.isfinite(high) and low < high):
        raise ValueError(f"input.invalid_argument: view {name}: MIN ska vara mindre än MAX och båda ändliga")
    return (low, high)


def _compare(state, rest):
    """view compare add: senaste mätningen blir jämförelsekurva i nästa fönster; clear tar bort alla."""
    curves = state["view"]["compare"]
    if rest == ["clear"]:
        curves.clear()
        out.say("view compare: 0 kurvor")
        return
    if rest != ["add"]:
        raise ValueError("input.invalid_argument: view compare tar add eller clear")
    spectrum = registry.need_spectrum(state)
    label = f"jämförelse {len(curves) + 1} ({time.strftime('%H:%M:%S')})"
    curves.append({"x": spectrum["x"].copy(), "values": calc.masked_values(spectrum),
                   "x_label": spectrum["x_label"], "y_label": spectrum["y_label"], "label": label})
    out.say(f"view compare: {len(curves)} kurvor, senast {label}")


def _analysis(state, rest):
    """view analysis NAMN väljer panelen till höger om spektrumet i nästa fönster; off tar bort den. Beräknar inget."""
    registry.need(rest, ("NAMN",), "view analysis")
    name = rest[0]
    if name != "off" and name not in display.PANELS:
        raise ValueError(f"input.invalid_argument: okänd panel {name}, välj {', '.join(display.PANELS)} eller off")
    state["view"]["analysis"] = None if name == "off" else name
    out.say(f"view analysis: {name}")


@registry.command("graf", "visa senaste mätningen i ett fönster; stäng fönstret för att fortsätta")
def cmd_graf(state, args):
    """Kommandot graf: senaste mätningen med samma rubrik och rutor som live, i ett fönster som väntar tills det stängs."""
    registry.need(args, (), "graf")
    spectrum = registry.need_spectrum(state)
    masked = calc.masked_values(spectrum)
    win = plot.open_plot()
    try:
        win.update(display.window_info(state))
        win.update(display.frame_info(state, win, spectrum, masked))
        display.draw_spectrum(state, win, spectrum, masked)
        out.say("Stäng fönstret (krysset) för att komma tillbaka till prompten.")
        plot.show()
    finally:
        plot.close(win)
