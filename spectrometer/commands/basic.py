"""help, quit, show, status och version."""

import sys

from spectrometer import meta, out, registry, session

GROUP = "grund"  # help.grund visar modulens kommandon


GROUP_TEXT = {  # help.NAMN: rubriken och vad gruppen har, i den ordning help visar grupperna
    "grund": ("Grunden", "läget, ångra, historik, kommandofiler, guide och avsluta"),
    "kalla": ("Källa och bild", "källa, ROI, kanal, kameran och hur raderna blir ett spektrum"),
    "kalibrera": ("Kalibrering", "våglängd, mörker, respons, referens och transmission"),
    "mata": ("Mäta och spara", "step, save, live, fönstret, serier och uppställningen"),
    "analys": ("Analys", "läsa mätningar, toppar, färg, bandgap, figurer och noggrannhet"),
}

QUICKSTART = (  # help.snabbstart: samma steg som guide (STEPS i demo_cmds), med exempel
    "Snabbstart: en mätning från start till sparad mapp.",
    "",
    "Prova först utan kamera (i projektmappen):",
    "  source file tests/data/bilder/rand_x12.png",
    "  step                        ska ge Topp 200 vid pixel 12 (1 bild)",
    "  save                        sparar i data/ÅÅÅÅMMDD-HHMMSS",
    "",
    "En riktig mätning, i den här ordningen:",
    "  1. source camera 0          välj kameran (cameras visar vilka som ger bild)",
    "  2. roi X Y W H              delen av bilden som mäts (roi auto föreslår en)",
    "  3. dark                     mörker med blockerad ljusväg",
    "  4. calibrate PUNKTFIL.csv   pixel till nm (se exempel/kalibrering/README.md)",
    "  5. response build KÄND.csv  responsen ur en känd lampa, sedan response on",
    "  6. step                     mät och skriv toppen (graf visar mätningen)",
    "  7. save                     spara mätningen",
    "",
    "guide visar stegen med x för det som är gjort; status visar nästa steg.",
    "Transmission: reference utan prov, mode transmission, sedan step med provet.",
    "Programmet minns inget mellan två starter: kör dark, calibrate och response build igen.",
    "Talen är relativa (counts, inte watt eller lumen); help limits säger vad de inte betyder.",
)


def _plain(text):
    """Gemener utan å, ä och ö, så att help.Mäta och help.mata är samma grupp."""
    return text.lower().translate(str.maketrans("åäö", "aao"))


def _overview():
    """help ensam: snabbstarten och grupperna, en rad var, och hur man går vidare."""
    rows = [("help.snabbstart", "Ny här? En mätning steg för steg")]
    rows += [(f"help.{key}", f"{title}: {what} ({len(registry.GROUPS[key])})")
             for key, (title, what) in GROUP_TEXT.items() if registry.GROUPS.get(key)]
    width = max(len(left) for left, _ in rows)
    out.say("Kommandona står i grupper. Skriv help.GRUPP för att se en grupp, till exempel help.mata:")
    out.table([(left.ljust(width), right) for left, right in rows], "  ")
    out.say("help KOMMANDO visar ett kommando och hur det skrivs; help alla visar alla kommandon.")


def _group(key):
    """help.GRUPP: rubriken och en rad per kommando i gruppen."""
    title, what = GROUP_TEXT[key]
    rows = [(name, registry.COMMANDS[name].text) for name in registry.GROUPS.get(key, [])]
    width = max((len(name) for name, _ in rows), default=0)
    out.say(f"{title}: {what}")
    out.table([(name.ljust(width), text) for name, text in rows], "  ")
    out.say("help KOMMANDO visar hur ett kommando skrivs.")


@registry.command("help", "Visa grupperna; help.GRUPP visar en grupp, help.snabbstart hur man mäter",
                  "help [GRUPP|snabbstart|alla|KOMMANDO], eller help.GRUPP")
def cmd_help(state, args):
    """Kommandot help [GRUPP|snabbstart|alla|KOMMANDO]: grupperna, en grupp, snabbstarten, alla kommandon eller ett.

    help.mata är samma sak som help mata (registry.canonical gör om punkten).
    """
    what = _plain(" ".join(args))
    if not what:
        _overview()
    elif what == "snabbstart":
        for line in QUICKSTART:
            out.say(line)
    elif what in GROUP_TEXT:
        _group(what)
    else:
        lines = registry.help_lines() if what == "alla" else registry.help_for(" ".join(args))
        out.table([line.split(" ", 1) for line in lines], " ")  # help history save: två ord, ett kommando


def _really_quit(state):
    """quit i en terminal med en osparad mätning frågar först. Ger True om programmet ska avsluta. UX-06."""
    spectrum = state["spectrum"]
    if spectrum is None or "saved_in" in spectrum or not sys.stdin.isatty():
        return True
    try:
        answer = out.ask("Mätningen är inte sparad. Avsluta ändå? (j/n) ")
    except EOFError:
        return True
    return answer.strip().lower() in ("j", "ja")


@registry.command("quit", "Avsluta")
def cmd_quit(state, args):
    """Kommandot quit: skriver Avslutar. och ber main att avsluta (svarar True); frågar först om en osparad mätning."""
    registry.need(args, (), "quit")
    if not _really_quit(state):
        return None
    out.say("Avslutar.")
    return True


def _describe(key, value):
    """En rad i show med vanliga ord: källa: fil x.png, roi: hela bilden, mätning: ja. Andra nycklar: nyckel: värde."""
    if key == "source":
        kind, where = value
        return f"källa: {'fil' if kind == 'file' else 'kamera'} {where}"
    if key == "roi":
        return "roi: hela bilden" if value is None else "roi: " + " ".join(str(n) for n in value)
    if key == "mätning":
        return f"mätning: {'nej' if value is None else 'ja'}"
    return f"{key}: {value}"


@registry.command("show", "Visa inställningarna")
def cmd_show(state, args):
    """Kommandot show: inställningarna, kalibrering, mörker, respons, referens, mode och om en mätning finns."""
    registry.need(args, (), "show")
    for key, value in state["settings"].items():
        out.say(_describe(key, value))
    out.say(f"kalibrering: {out.YES[state['coefficients'] is not None]}")
    out.say(f"mörker: {out.YES[state['dark'] is not None]}{_age(state, 'dark')}")
    use = "on" if state["use_response"] else "off"
    unused = " (används inte i mode transmission)" if state["use_response"] and state["mode"] == "transmission" else ""
    out.say(f"respons: {out.YES[state['response'] is not None]}, {use}{unused}")
    out.say(f"referens: {out.YES[state['reference'] is not None]}{_age(state, 'reference')}")
    out.say(f"mode: {state['mode']}")
    out.say(_describe("mätning", state["spectrum"]))
    for line in session.extra_lines(state):  # bara det du valt (kamera, serie, anteckning)
        out.say(line)


def _next_step(state):
    """Nästa steg i kedjan dark, calibrate, response build, reference; step när allt finns."""
    if state["dark"] is None:
        return "dark (blockera ljusvägen)"
    if state["coefficients"] is None:
        return "calibrate FIL"
    if state["response"] is None:
        return "response build FIL"
    if state["reference"] is None:
        return "reference (utan prov)"
    return "step"


@registry.command("status", "Visa kedjan och nästa steg")
def cmd_status(state, args):
    """Kommandot status: mörker, kalibrering, respons, referens och läge på en rad, sedan nästa steg i kedjan."""
    registry.need(args, (), "status")
    parts = [
        f"mörker {out.YES[state['dark'] is not None]}",
        f"kalibrering {out.YES[state['coefficients'] is not None]}",
        f"respons {out.YES[state['response'] is not None]}",
        f"referens {out.YES[state['reference'] is not None]}",
        f"läge {state['mode']}",
    ]
    out.say("  ".join(parts))
    out.say(f"Nästa: {_next_step(state)}")


@registry.command("version", "Visa versionerna av programmet och biblioteken")
def cmd_version(state, args):
    """Kommandot version: programmet, Python, biblioteken, git och operativsystemet på en rad."""
    registry.need(args, (), "version")
    out.say(meta.version_line())


def _age(state, what):
    """Texten efter ja i show: " (för 47 min sedan)" när what är minst AGE_SHOWN_MIN min gammalt, annars tom. PRO-11."""
    minutes = session.age_minutes(state, what)
    return f" (för {minutes} min sedan)" if minutes is not None and minutes >= session.AGE_SHOWN_MIN else ""
