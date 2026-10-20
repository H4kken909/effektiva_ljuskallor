"""Kommandoregistret: @command märker en funktion, load() bygger registret, run_command() kör en rad.

help byggs ur registret i FEATURES-ordning och sedan i den ordning funktionerna står i sina filer
(facit_04 jämför help rad för rad). need() och to_int() är argumentkontrollerna som alla kommandon delar.
"""

import os
import shlex
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Ett kommando: namnet, texten efter namnet i help och funktionen run(state, args)."""

    name: str
    text: str
    run: Callable


COMMANDS: dict[str, Command] = {}


def command(name, text):
    """Märk funktionen som kommandot name; load() registrerar den."""

    def mark(func):
        func.spektro_command = Command(name, text, func)
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


def run_command(state, line):
    """Delar en rad i ord och kör kommandot.

    Returnerar: kommandots svar: True från quit, annars None (också för en tom rad).
    Fel: ValueError med input.invalid_argument vid citattecken utan slut eller okänt kommando; kommandots egna fel.
    """
    if os.name == "nt":
        line = line.replace("\\", "\\\\")  # Windows: annars tar shlex bort bakåtsnedstrecken i C:\bilder\a.png
    try:
        words = shlex.split(line)
    except ValueError as error:
        raise ValueError("input.invalid_argument: citattecken saknar slut") from error
    if not words:
        return None  # tom rad: bara en ny prompt
    if words[0] not in COMMANDS:
        raise ValueError(f"input.invalid_argument: okänt kommando {words[0]}. Skriv help för en lista.")
    return COMMANDS[words[0]].run(state, words[1:])


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
