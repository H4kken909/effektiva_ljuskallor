"""exposure, gain och auto: kamerans reglage som du väljer. Krav 18 och 21 (serier) kräver fast exponering.

Talen är drivrutinens egna, utan enhet (V4L2 och DirectShow räknar olika). Valet står i state["controls"], sätts
varje gång kameran öppnas (step, start, dark ...) och sparas i settings.json. info visar vad drivrutinen säger.
"""

import math

from spectrometer import measure, out, registry, session, source


def _number(name, text):
    """Ett ändligt tal; får vara negativt (DirectShow har exponering som -6)."""
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: {name} ska vara ett tal, fick {text}") from error
    if not math.isfinite(value):
        raise ValueError(f"input.invalid_argument: {name} ska vara ett ändligt tal")
    return value


def _choose(state, name, value):
    """Sparar valet (en ny ordbok, så att undo fungerar), glömmer mätningen.

    Bara när källan är en kamera provas valet direkt (öppnar, sätter, läser tillbaka).
    """
    state["controls"] = state["controls"] | {name: value}
    state["spectrum"] = None
    chosen = session.controls_text({name: value})
    if state["settings"]["source"][0] != "camera":
        out.say(f"{chosen} (sätts när kameran öppnas)")
        return
    said = measure._with_source(state, source.get_controls)[name]  # öppnar, sätter, läser tillbaka, stänger
    out.say(f"{chosen} (drivrutinen säger {session.controls_text({name: said}) or f'{name} okänt'})")


@registry.command("exposure", "N: kamerans exponering i drivrutinens tal (fast exponering för serier)", "exposure N")
def cmd_exposure(state, args):
    """Kommandot exposure N: exponeringen som sätts varje gång kameran öppnas. Kör auto off först."""
    registry.need(args, ("N",), "exposure")
    _choose(state, "exposure", _number("N", args[0]))


@registry.command("gain", "N: kamerans förstärkning i drivrutinens tal", "gain N")
def cmd_gain(state, args):
    """Kommandot gain N: förstärkningen som sätts varje gång kameran öppnas."""
    registry.need(args, ("N",), "gain")
    _choose(state, "gain", _number("N", args[0]))


@registry.command("auto", "on|off: kamerans auto-exponering (off för serier, Krav 18 och 21)", "auto on eller auto off")
def cmd_auto(state, args):
    """Kommandot auto on eller auto off: med auto på ändrar kameran exponeringen själv, och då går serier inte att jämföra."""
    if args not in (["on"], ["off"]):
        raise ValueError("input.invalid_argument: auto tar on eller off")
    _choose(state, "auto", args[0] == "on")
