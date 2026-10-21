"""guide, pause och help limits: demoflödet så att Jawad kan mäta själv (W22), och vad talen inte säger."""

import sys

from spectrometer import out, registry

GROUP = "grund"  # help.grund visar modulens kommandon

STEPS = (  # stegen för en mätning i ordning: namnet och kommandot som gör det
    ("källa", "source camera N eller source file BILD"),
    ("ROI", "roi X Y W H (roi auto föreslår)"),
    ("mörker", "dark (blockera ljusvägen)"),
    ("kalibrering", "calibrate PUNKTFIL.csv"),
    ("respons", "response build KÄND.csv och response on"),
    ("mätning", "step"),
    ("sparad", "save"),
)

LIMITS = (  # help limits och README, avsnittet Begränsningar: samma rader
    "Intensiteten är relativ: kameran ger counts, inte watt, lumen eller verkningsgrad.",
    "8 bitar: varje pixel är 0–255; vid 255 är den mättad och toppen blir för låg (step varnar).",
    "Fönstret är 366–766 nm med KO-kalibreringen: utanför finns ingen kalibrerad våglängd.",
    "Upplösningen är FWHM för en smal linje (laser eller lysrörets 576,96 och 579,07 nm); calibrate save skriver den.",
    "Färg och färgtemperatur kräver response on; färgtemperaturen gäller bara nära svartkroppskurvan.",
    "Bandgapet är brantaste lutningen extrapolerad till A = 0; osäkerheten är bara ±0,5 pixelsteg.",
    "Testerna visar att räkningen stämmer, inte att instrumentet mäter rätt.",
)


def _done(state):
    """Vilka av STEPS som är gjorda, ur state, i samma ordning. Källan finns alltid (kamera 0 från början)."""
    spectrum = state["spectrum"]
    return [
        True,
        state["settings"]["roi"] is not None,
        state["dark"] is not None,
        state["coefficients"] is not None,
        state["use_response"],
        spectrum is not None,
        spectrum is not None and "saved_in" in spectrum,
    ]


@registry.command("guide", "stegen för en mätning med x för det som är gjort, och nästa steg")
def cmd_guide(state, args):
    """Kommandot guide: källa, ROI, mörker, kalibrering, respons, mätning och sparad, med x för det som är gjort."""
    registry.need(args, (), "guide")
    kind, value = state["settings"]["source"]
    source = f"{'kamera' if kind == 'camera' else 'fil'} {value}"
    done = _done(state)
    for (name, command), ok in zip(STEPS, done):
        what = f"{source} (byt med {command})" if name == "källa" else command
        out.say(f"[{'x' if ok else ' '}] {name:<12} {what}")
    missing = [command for (_name, command), ok in zip(STEPS, done) if not ok]
    out.say(f"Nästa: {missing[0]}" if missing else "Allt gjort. Nästa mätning: step och save; color för färgen.")


@registry.command("pause", "TEXT: skriv texten och vänta på Enter (i en kommandofil: tid att byta lampa)", "pause TEXT")
def cmd_pause(state, args):
    """Kommandot pause TEXT: skriver TEXT och väntar på Enter i en terminal; avbryt stoppar kommandofilen.

    Pipad (facit, tester) skrivs bara texten. Fel: ValueError med input.invalid_argument utan TEXT eller vid avbryt.
    """
    if not args:
        raise ValueError("input.invalid_argument: pause: TEXT saknas")
    text = " ".join(args)
    if not sys.stdin.isatty():
        out.say(text)
        return
    try:
        answer = out.ask(f"{text}. Tryck Enter (avbryt stoppar): ")
    except EOFError:
        answer = "avbryt"
    if answer.strip().lower() == "avbryt":
        raise ValueError("input.invalid_argument: avbrutet vid pause")


@registry.command("help limits", "programmets begränsningar: vad talen betyder och inte betyder")
def cmd_help_limits(state, args):
    """Kommandot help limits: en rad per begränsning i LIMITS (samma rader som i README, Begränsningar)."""
    registry.need(args, (), "help limits")
    for line in LIMITS:
        out.say(line)
