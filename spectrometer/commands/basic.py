"""help, quit, show, status och version."""

import sys

from spectrometer import meta, out, registry, session


@registry.command("help", "Visa kommandona", "help [KOMMANDO]")
def cmd_help(state, args):
    """Kommandot help [KOMMANDO]: en rad per kommando i registret, eller raden och syntaxen för ett kommando."""
    if not args:
        lines = registry.help_lines()
    else:
        lines = registry.help_for(" ".join(args))  # två ord för tvåordskommandon: help history save
    out.table([line.split(" ", 1) for line in lines], " ")


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
    calibration = "ja" if state["coefficients"] is not None else "nej"
    dark = "ja" if state["dark"] is not None else "nej"
    response = "ja" if state["response"] is not None else "nej"
    reference = "ja" if state["reference"] is not None else "nej"
    use = "on" if state["use_response"] else "off"
    out.say(f"kalibrering: {calibration}")
    out.say(f"mörker: {dark}{_age(state, 'dark')}")
    unused = " (används inte i mode transmission)" if state["use_response"] and state["mode"] == "transmission" else ""
    out.say(f"respons: {response}, {use}{unused}")
    out.say(f"referens: {reference}{_age(state, 'reference')}")
    out.say(f"mode: {state['mode']}")
    out.say(_describe("mätning", state["spectrum"]))
    for line in session.extra_lines(state):  # 1.2.x: bara det du valt (kamera, serie, anteckning)
        out.say(line)


def _next_step(state):
    """Nästa steg i kedjan dark, calibrate, response build, reference; step när allt finns. Ren funktion."""
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
    """Texten efter ja i show: " (för 47 min sedan)" när what är minst AGE_SHOWN_MIN minuter gammalt, annars tom. PRO-11."""
    minutes = session.age_minutes(state, what)
    return f" (för {minutes} min sedan)" if minutes is not None and minutes >= session.AGE_SHOWN_MIN else ""
