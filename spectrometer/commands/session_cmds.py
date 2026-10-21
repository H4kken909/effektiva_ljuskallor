"""reset, undo, history, clear och set: nollställ, ångra, se och spara raderna vid prompten,
ta bort en del av kedjan och ändra en gräns."""

import sys
from datetime import datetime

from spectrometer import out, registry, session

PARTS = {  # clear NAMN: nycklarna i state som töms, och raden som skrivs
    "dark": (("dark", "dark_frames", "dark_camera"), "mörker: borttaget"),
    "calibration": (("coefficients", "pixel_range", "fit_range", "calibration_points_file"),
                    "kalibrering: borttagen, x är pixlar igen"),
    "response": (("response",), "respons: borttagen"),
    "reference": (("reference",), "referens: borttagen"),
}
NOT_SAVED = ("help", "show", "status", "version", "history", "undo", "quit")  # history save hoppar över dem
SETTABLE = ("min_response", "min_reference", "output_dir")  # nycklarna som set får ändra


def _lost(state):
    """Det reset tar bort, med namn: mörker, kalibrering, respons och referens, de som finns."""
    names = (("mörker", "dark"), ("kalibrering", "coefficients"), ("respons", "response"), ("referens", "reference"))
    return [name for name, key in names if state[key] is not None]


def _renew(state, settings):
    """Tömmer state och bygger en ny med settings; start_settings (det reset går tillbaka till) står kvar."""
    start = state.get("start_settings")
    state.clear()
    state.update(session.new_state(settings))
    state["start_settings"] = start


@registry.command("reset", "[ja]: nollställ allt som vid start (i en terminal med mörker eller kalibrering: reset ja)",
                  "reset eller reset ja")
def cmd_reset(state, args):
    """Kommandot reset [ja]: ny state med DEFAULTS. I en terminal frågar det först om något går förlorat; undo ångrar.

    Fel: ValueError med input.invalid_argument om ordet efter reset inte är ja.
    """
    if args not in ([], ["ja"]):
        raise ValueError("input.invalid_argument: reset tar inget ord, eller ja")
    lost = _lost(state)
    if lost and not args and sys.stdin.isatty():
        out.say(f"Du förlorar {', '.join(lost)}. Skriv reset ja för att fortsätta.")
        return
    start = state.get("start_settings")  # inställningarna vid start, med --output, --input och --camera
    _renew(state, start or session.DEFAULTS)
    out.say("Allt nollställt (som vid start).")


@registry.command("undo", f"ångra senaste raden vid prompten som ändrade något (högst {registry.UNDO_STEPS} steg)")
def cmd_undo(state, args):
    """Kommandot undo: lägger tillbaka state från före senaste ändrande raden vid prompten; mätningen glöms.

    Fel: ValueError med input.missing_data när inget finns att ångra (rader i run FIL ångras som en enda rad).
    """
    registry.need(args, (), "undo")
    steps = state.get("undo") or []
    if not steps:
        raise ValueError("input.missing_data: inget att ångra")
    index, before = steps.pop()
    entry = state["history"][index]
    entry[1] = "ångrad"  # history save hoppar över den
    session.restore(state, before)
    out.say(f"Ångrat: {entry[0]}")


@registry.command("history", "[N]: de N senaste raderna vid prompten (20), fel och ångrade märkta", "history [N]")
def cmd_history(state, args):
    """Kommandot history [N]: de N senaste raderna som skrevs vid prompten, numrerade från början av sessionen."""
    registry.at_most_one(args, "history", "N")
    n = registry.to_int("N", args[0], 1) if args else 20
    history = state.get("history") or []
    if not history:
        out.say("history: inga rader än")
        return
    first = max(0, len(history) - n)
    for number, (line, status) in enumerate(history[first:], start=first + 1):
        mark = "" if status == "ok" else f"  ({status})"
        out.say(f"{number:3d}  {line}{mark}")


def _name(line):
    """Kommandots namn i en rad: första ordet med gemener, kortformer som q blir quit."""
    words = line.removeprefix("spektro>").split()
    return registry.ALIASES.get(words[0].lower(), words[0].lower()) if words else ""


@registry.command("history save", "FIL: spara raderna som lyckades som en kommandofil (för run FIL)",
                  "history save FIL")
def cmd_history_save(state, args):
    """Kommandot history save FIL: raderna utan fel och inte ångrade, utan NOT_SAVED, i en ny kommandofil.

    Fel: ValueError med input.invalid_argument om FIL redan finns (skriver aldrig över); OSError om den inte går att
    skriva.
    """
    registry.need(args, ("FIL",), "history save")
    lines = [line for line, status in state.get("history") or [] if status == "ok" and _name(line) not in NOT_SAVED]
    with registry.open_new(args[0], "x", "history save", encoding="utf-8") as f:
        f.write(f"# history save {datetime.now():%Y-%m-%d %H:%M}: raderna som lyckades vid prompten\n")
        for line in lines:
            f.write(f"{line}\n")
    out.say(f"history: {len(lines)} rader sparade i {args[0]}")


@registry.command("clear",
                  "dark|calibration|response|reference|all: ta bort en del av kedjan, inställningarna står kvar",
                  "clear dark, clear calibration, clear response, clear reference eller clear all")
def cmd_clear(state, args):
    """Kommandot clear NAMN: tar bort mörker, kalibrering, respons eller referens; all tar alla fyra, inget annat.
    Senaste mätningen glöms alltid (den mättes med det borttagna); inställningar, reglage, serie, note och vy står kvar.

    Det som mättes med det borttagna glöms också: dark tar referensen, calibration tar respons och referens (x i nm).
    Utan referens lämnas mode transmission (mode blir direct och det skrivs).
    Fel: ValueError med input.invalid_argument vid ett okänt namn.
    """
    registry.need(args, ("NAMN",), "clear")
    name = args[0]
    if name == "all":
        for keys, _ in PARTS.values():
            for key in keys:
                state[key] = None
        state["use_response"] = False
        state["spectrum"] = None
        out.say("Mörker, kalibrering, respons och referens borttagna. Inställningarna står kvar.")
        session.leave_transmission(state)
        return
    if name not in PARTS:
        raise ValueError("input.invalid_argument: clear: välj dark, calibration, response, reference eller all")
    if name == "calibration":
        session.forget_response(state)
    if name in ("dark", "calibration"):
        session.forget_reference(state)
    keys, text = PARTS[name]
    for key in keys:
        state[key] = None
    if state["response"] is None:
        state["use_response"] = False
    state["spectrum"] = None
    out.say(text)
    if state["reference"] is None:
        session.leave_transmission(state)


@registry.command("set", "min_response TAL, min_reference TAL eller output_dir MAPP: ändra en gräns eller mappen",
                  "set min_response TAL, set min_reference TAL eller set output_dir MAPP")
def cmd_set(state, args):
    """Kommandot set NYCKEL VÄRDE för min_response och min_reference (ändliga tal över 0) och output_dir.

    Mätningen glöms, som när en inställning ändras. Fel: ValueError med input.invalid_argument vid en annan nyckel.
    """
    registry.need(args, ("NYCKEL", "VÄRDE"), "set")
    key, text = args
    if key not in SETTABLE:
        raise ValueError(f"input.invalid_argument: set: okänd nyckel {key}, välj {', '.join(SETTABLE)}")
    value = text if key == "output_dir" else registry.to_float(key, text, 0)
    session.set_setting(state, key, value)
    out.say(f"{key}: {value}")
