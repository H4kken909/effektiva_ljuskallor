"""Kommandoregistret: @command märker en funktion, load() bygger registret, run_command() kör en rad.

help byggs ur registret i FEATURES-ordning och sedan i den ordning funktionerna står i sina filer
(facit_04 jämför help rad för rad). need() och to_int() är argumentkontrollerna som alla kommandon delar.
Hjälparna masked_values och roi_or_whole, som kommandona delar, ligger i calc.py.
"""

import difflib
import os
import shlex
import sys
from collections.abc import Callable
from dataclasses import dataclass

from spectrometer import out, session


@dataclass(frozen=True)
class Command:
    """Ett kommando: namnet, texten efter namnet i help och funktionen run(state, args)."""

    name: str
    text: str
    run: Callable
    usage: str = ""  # syntaxen (help KOMMANDO visar den från 1.0.40), tom om den saknas


COMMANDS: dict[str, Command] = {}
ALIASES = {"h": "help", "?": "help", "q": "quit", "exit": "quit"}  # kortformer, slås upp före COMMANDS


def command(name, text, usage=""):
    """Märk funktionen som kommandot name; load() registrerar den. usage är kommandots syntax (kan saknas)."""

    def mark(func):
        func.spektro_command = Command(name, text, func, usage)
        return func

    return mark


def load(modules):
    """Bygg registret ur modulerna i given ordning. Samma namn två gånger är ett fel."""
    COMMANDS.clear()
    for module in modules:
        for obj in vars(module).values():
            cmd = getattr(obj, "spektro_command", None)
            if cmd is None:
                continue
            if cmd.name in COMMANDS:
                raise ValueError(f"kommandot {cmd.name} finns två gånger")
            COMMANDS[cmd.name] = cmd


def help_lines():
    """Raderna som help skriver, en per kommando."""
    return [f"{c.name} {c.text}" for c in COMMANDS.values()]


def lookup(name):
    """Kommandot name i registret.

    Fel: ValueError med input.invalid_argument om kommandot inte finns.
    """
    if name not in COMMANDS:
        close = difflib.get_close_matches(name, COMMANDS, n=1)
        hint = f" Menade du {close[0]}?" if close else ""
        raise ValueError(f"input.invalid_argument: okänt kommando {name}.{hint} Skriv help för en lista.")
    return COMMANDS[name]


def help_for(name):
    """Raderna för help KOMMANDO (från 1.0.40): samma rad som help, och Användning: om kommandot har en syntax."""
    cmd = lookup(name)
    lines = [f"{cmd.name} {cmd.text}"]
    if cmd.usage:
        lines.append(f"Användning: {cmd.usage}")
    return lines


def run_command(state, line):
    """Delar en rad i ord och kör kommandot.

    Returnerar: kommandots svar: True från quit, annars None (också för en tom rad).
    Fel: ValueError med input.invalid_argument vid citattecken utan slut eller okänt kommando; kommandots egna fel.
    """
    if os.name == "nt":
        line = line.replace("\\", "\\\\")  # Windows: annars tar shlex bort bakåtsnedstrecken i C:\bilder\a.png
    try:
        # comments=True: allt efter # är en kommentar. En inklistrad rad ur facit (spektro> step) fungerar också.
        words = shlex.split(line.lstrip().removeprefix("spektro>"), comments=True)
    except ValueError as error:
        raise ValueError("input.invalid_argument: citattecken saknar slut") from error
    if not words:
        return None  # tom rad: bara en ny prompt
    words[0] = ALIASES.get(words[0].lower(), words[0].lower())
    pair = " ".join(words[:2])
    if pair in COMMANDS:  # tvåordskommando, till exempel history save
        return COMMANDS[pair].run(state, words[2:])
    return lookup(words[0]).run(state, words[1:])


def need(args, names, name):
    """Kontrollerar att kommandot name fick lika många ord som names.

    Fel: ValueError med input.invalid_argument när ett ord saknas (felet säger vilket) eller när orden är för många.
    """
    if len(args) < len(names):
        raise ValueError(f"input.invalid_argument: {name}: {names[len(args)]} saknas")
    if len(args) > len(names):
        raise ValueError(f"input.invalid_argument: {name}: för många ord, väntade {len(names)}")


def to_int(name, text, smallest):
    """Gör om ett ord till ett heltal som är minst smallest.

    Fel: ValueError med input.invalid_argument om ordet inte är ett heltal eller är mindre än smallest.
    """
    try:
        number = int(text)
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: {name} ska vara ett heltal, fick {text}") from error
    if number < smallest:
        raise ValueError(f"input.invalid_argument: {name} ska vara minst {smallest}")
    return number


def to_float(name, text, above):
    """Gör om ett ord till ett ändligt tal som är större än above.

    Fel: ValueError med input.invalid_argument om ordet inte är ett tal, är inf eller nan, eller inte är större än
    above.
    """
    try:
        number = float(text)
    except ValueError as error:
        raise ValueError(f"input.invalid_argument: {name} ska vara ett tal, fick {text}") from error
    if not above < number < float("inf"):  # nan och inf blir också fel
        raise ValueError(f"input.invalid_argument: {name} ska vara ett ändligt tal större än {above:g}")
    return number


UNDO_STEPS = 5  # så många ändringar undo kan gå tillbaka; varje steg håller kvar sina bilder (mörkret) i minnet


def run_line(state, line):
    """Kör en rad som skrevs vid prompten: som run_command, men raden sparas i state["history"] och kan ångras.

    Ändrade raden något (session.changed) läggs state från före raden sist i state["undo"], högst UNDO_STEPS.
    En hel run FIL är en rad: undo ångrar hela filen.
    Returnerar: som run_command. Fel: som run_command; raden sparas då med status fel.
    """
    history = state.setdefault("history", [])
    steps = state.setdefault("undo", [])
    before, count = session.snapshot(state), len(steps)
    status = "fel"
    try:
        result = run_command(state, line)
        status = "ok"
        return result
    finally:
        state["history"], state["undo"] = history, steps  # reset och clear all tömmer state, men inte de här två
        if line.strip():
            if len(steps) == count and session.changed(state, before):  # undo tar själv bort ett steg: inget nytt
                steps.append((len(history), before))
                del steps[:-UNDO_STEPS]
            history.append([line.strip(), status])


MAX_FRAMES = 1000  # högst så många bilder i frames, dark och reference; 1000 bilder i 640x480 är ca 0,9 GB i minnet


def to_frames(text):
    """Antalet bilder N ur ett ord: ett heltal från 1 till MAX_FRAMES. KOM-39.

    Fel: ValueError med input.invalid_argument om ordet inte är ett heltal, är mindre än 1 eller större än MAX_FRAMES.
    """
    n = to_int("N", text, 1)
    if n > MAX_FRAMES:
        raise ValueError(f"input.invalid_argument: N ska vara högst {MAX_FRAMES}")
    return n


def at_most_one(args, name, what):
    """Fel om kommandot name fick fler än ett ord. what är ordets namn i felraden, till exempel N.

    Fel: ValueError med input.invalid_argument.
    """
    if len(args) > 1:
        raise ValueError(f"input.invalid_argument: {name} tar högst ett ord ({what})")


def plural(n, one, many):
    """Antalet med ordet i rätt form: plural(1, "bild", "bilder") är "1 bild", plural(5, ...) är "5 bilder"."""
    return f"{n} {one if n == 1 else many}"


def ready(state, prompt):
    """Kamera i en terminal: väntar på Enter efter prompten. Ger False om svaret är avbryt (fil eller pipad: True)."""
    if state["settings"]["source"][0] != "camera" or not sys.stdin.isatty():
        return True
    try:
        answer = out.ask(prompt)
    except EOFError:
        return False
    return answer.strip().lower() != "avbryt"


def need_spectrum(state):
    """Senaste mätningen. Fel: ValueError med input.missing_data om det inte finns någon."""
    spectrum = state["spectrum"]
    if spectrum is None:
        raise ValueError("input.missing_data: Ingen mätning än. Kör step först.")
    return spectrum


def open_new(path, mode, name, **options):
    """Öppnar path för skrivning, bara om filen inte finns. mode är "x" (text) eller "xb" (bytes).

    "x" och en öppen fil gör också att np.save och np.savez inte lägger till .npy eller .npz själva.
    Fel: ValueError med input.invalid_argument om filen redan finns; name säger vilket kommando som inte skriver över.
    """
    try:
        return open(path, mode, **options)
    except FileExistsError as error:
        raise ValueError(f"input.invalid_argument: {path} finns redan, {name} skriver inte över") from error
