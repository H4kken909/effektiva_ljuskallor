"""note och series: anteckning och metadata till varje save, och mätserier med en rad per mätning i serie.csv. 1.2.1.

Krav 18 och 21: varje punkt i en serie bär ström, spänning och vad som mättes. Ordningen vid riggen:
series start NAMN, series note current_mA=20 voltage_V=2.9, step, save, nästa ström ..., series stop.
"""

import re
from pathlib import Path

from spectrometer import display, out, plot, registry, session
from spectrometer.analysis import series

NUMBERS = ("current_mA", "voltage_V")  # tal, ändliga och större än 0
TEXTS = ("led", "sample", "lamp")  # ett ord, till exempel led=röd sample=ny


@registry.command("note", "[TEXT...]: anteckning som varje save skriver (note ensam visar den, note clear tar bort)",
                  "note [TEXT...] eller note clear")
def cmd_note(state, args):
    """Kommandot note TEXT: fri text till settings.json (och serie.csv) vid varje save, tills den byts. Mätningen står kvar."""
    if args == ["clear"]:
        state["note"] = None
    elif args:
        state["note"] = " ".join(args)
    out.say(f"note: {state['note'] or '(ingen)'}")


def _rows(path):
    """Antalet rader i serie.csv, 0 om filen inte finns än."""
    return len(series.load(path)) if Path(path).is_file() else 0


@registry.command("series start", "NAMN: börja en mätserie; save sparar i output_dir/NAMN och skriver en rad i serie.csv",
                  "series start NAMN")
def cmd_series_start(state, args):
    """Kommandot series start NAMN: mätmapparna i output_dir/NAMN och en rad per save i serie.csv där; finns den fortsätter den."""
    registry.need(args, ("NAMN",), "series start")
    name = args[0]
    if not re.fullmatch(r"[\w-]+", name):
        raise ValueError(f"input.invalid_argument: NAMN får ha bokstäver, siffror, _ och -, fick {name}")
    folder = Path(state["settings"]["output_dir"]) / name
    state["series"] = {"name": name, "folder": folder.as_posix(), "file": (folder / "serie.csv").as_posix()}
    state["annotations"] = {}
    state["spectrum"] = None
    rows = _rows(state["series"]["file"])
    out.say(f"serie {name}: {state['series']['file']}" + (f", fortsätter efter {rows} rader" if rows else ""))


@registry.command("series note", "NYCKEL=VÄRDE...: current_mA, voltage_V, led, sample eller lamp för nästa mätning",
                  "series note current_mA=20 voltage_V=2.9 led=röd")
def cmd_series_note(state, args):
    """Kommandot series note NYCKEL=VÄRDE...: ström, spänning, LED, prov och lampa till varje save tills de byts.

    Glömmer mätningen: värdena beskriver nästa step. Fel: ValueError med input.invalid_argument vid okänd nyckel eller fel tal.
    """
    if not args:
        raise ValueError("input.invalid_argument: series note: NYCKEL=VÄRDE saknas")
    annotations = dict(state["annotations"])
    for word in args:
        key, sep, value = word.partition("=")
        if key in NUMBERS and sep:
            annotations[key] = registry.to_float(key, value, 0)
        elif key in TEXTS and value:
            annotations[key] = value
        else:
            raise ValueError(f"input.invalid_argument: series note: {word} ska vara NYCKEL=VÄRDE med en av "
                             f"{', '.join(NUMBERS + TEXTS)}")
    state["annotations"] = annotations
    state["spectrum"] = None
    out.say(f"series note: {session.annotations_text(annotations)}")


@registry.command("series stop", "avsluta mätserien; save sparar i output_dir igen")
def cmd_series_stop(state, args):
    """Kommandot series stop: skriver hur många rader serien fick och glömmer series note. Mätningen står kvar."""
    registry.need(args, (), "series stop")
    if state["series"] is None:
        raise ValueError("input.missing_data: ingen serie pågår. Kör series start NAMN")
    out.say(f"serie {state['series']['name']} stoppad: {_rows(state['series']['file'])} rader i {state['series']['file']}")
    state["series"] = None
    state["annotations"] = {}


AXES = {"current": ("current_mA", "mA", "ström (mA)"), "voltage": ("voltage_V", "V", "spänning (V)")}
POWER_LABEL = "relativ uteffekt (area, godtycklig enhet)"
DROOP_LABEL = "relativ effektivitet (area/I, max 1)"


def _plot_words(args):
    """Orden efter series plot som (namnen, x-axeln, droop, UT eller None). Fel: ValueError med input.invalid_argument."""
    words, axis = list(args), "current"
    if "--x" in words:
        k = words.index("--x")
        axis = words[k + 1] if k + 1 < len(words) else ""
        if axis not in AXES:
            raise ValueError("input.invalid_argument: series plot: --x tar current eller voltage")
        del words[k:k + 2]
    droop = "--droop" in words
    if droop and axis != "current":
        raise ValueError("input.invalid_argument: series plot: --droop är area/I och kräver --x current")
    target = next((word for word in words if word.lower().endswith((".png", ".svg"))), None)
    names = [word for word in words if word not in ("--droop", target)]
    if not names:
        raise ValueError("input.invalid_argument: series plot: NAMN saknas")
    return names, axis, droop, target


@registry.command("series plot", "NAMN... [--x current|voltage] [--droop] [UT.png]: relativ uteffekt mot ström, eller droop",
                  "series plot NAMN... [--x current|voltage] [--droop] [UT.png|UT.svg]")
def cmd_series_plot(state, args):
    """Kommandot series plot NAMN...: area mot ström (Krav 18), eller med --droop area/I delad med sitt max (Krav 21).

    En kurva per serie (output_dir/NAMN/serie.csv), så att nya och gamla dioder står i samma figur. Med UT.png sparas
    figuren, annars visas ett fönster. Allt är relativt: arean är aldrig watt, och droop jämför formen, inte nivån.
    """
    names, axis, droop, target = _plot_words(args)
    column, unit, x_label = AXES[axis]
    curves, found = [], []  # found: till droop-panelen (1.2.16)
    for name in names:
        path = Path(state["settings"]["output_dir"]) / name / "serie.csv"
        if not path.is_file():
            raise ValueError(f"input.missing_data: {path.as_posix()} finns inte. Kör series start {name} och save")
        xs, areas = series.table(series.load(path), column)
        xs, areas, spreads, counts = series.repeats(xs, areas)  # 1.2.14: samma ström flera gånger: medel ± spridning
        out.say(f"serie {name}: {xs.size} punkter ur {path.as_posix()}")
        eff = series.droop(xs, areas) if axis == "current" else None
        for k, (x, area) in enumerate(zip(xs, areas)):
            more = f", relativ effektivitet {out.fmt(eff[k])}" if eff is not None else ""
            times = f" ({counts[k]} mätningar)" if counts[k] > 1 else ""
            out.say(f"  {out.fmt(x)} {unit}: relativ uteffekt {out.pm(area, spreads[k])}{times}{more}")
        if eff is not None and xs.size >= 2:
            out.say(f"  droop: {100 * (1 - eff[-1]):.0f} % lägre area/I vid {out.fmt(xs[-1])} mA än vid max "
                    "(relativt, inte verkningsgrad)")
        if counts.max(initial=0) > 1:
            out.say("  ± är spridningen mellan upprepade mätningar vid samma ström; total osäkerhet ej kvantifierad")
        curves.append((xs, eff if droop else areas, name))
        found.append((name, xs, areas, eff))
    display.remember(state, "droop", {"curves": found, "x_label": x_label})  # 1.2.16: view analysis droop
    y_label = DROOP_LABEL if droop else POWER_LABEL
    if target is not None:
        plot.save_figure(target, curves, x_label, y_label)
        out.say(f"Sparad: {target}")
        return
    out.say("Stäng fönstret (krysset) för att komma tillbaka till prompten.")
    plot.show_spectra(curves, x_label, y_label)
