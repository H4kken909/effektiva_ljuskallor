"""run och wait: kör en kommandofil rad för rad, och vänta mellan två rader i en fil."""

import time

from spectrometer import out, registry

MAX_DEPTH = 5  # run i en fil som körs med run ...: högst fem nivåer (en fil som kör sig själv stannar här)
MAX_WAIT = 600  # wait väntar högst så många sekunder (10 min)

_depth = 0  # hur många run som pågår just nu


def command_lines(path):
    """Raderna i en kommandofil som ska köras: (radnummer, rad) utan tomma rader och rader som börjar med #.

    En rad inklistrad ur facit (spektro> step) blir step. Fel: OSError om filen inte går att läsa.
    """
    with open(path, encoding="utf-8-sig") as f:  # -sig: en fil från Anteckningar med BOM fungerar också
        rows = f.read().splitlines()
    lines = []
    for number, row in enumerate(rows, start=1):
        text = row.strip().removeprefix("spektro>").strip()
        if text and not text.startswith("#"):
            lines.append((number, text))
    return lines


def _with_place(error, path, number):
    """Samma sorts fel (ValueError, RuntimeError eller OSError) med (FIL rad N) sist; main skriver Fel: och texten."""
    kind = next(k for k in (ValueError, RuntimeError, OSError) if isinstance(error, k))
    tagged = kind(f"{error} ({path} rad {number})")
    tagged.run_line = True  # en yttre run lägger inte till sin rad också
    return tagged


@registry.command("run", "FIL: kör kommandona i en kommandofil, en rad i taget; stannar vid första felet", "run FIL")
def cmd_run(state, args):
    """Kommandot run FIL: kör raderna i FIL som om de skrevs vid prompten, och skriver spektro> RAD före svaret.

    Stannar vid första felet; raderna efter körs inte. quit i filen avslutar hela programmet.
    Returnerar: True om filen körde quit (main avslutar då), annars None.

    Fel: ValueError med input.invalid_argument vid mer än MAX_DEPTH nivåer run; felet från raden med (FIL rad N) sist.
    """
    global _depth
    registry.need(args, ("FIL",), "run")
    if _depth >= MAX_DEPTH:
        raise ValueError(f"input.invalid_argument: run: för många nivåer (högst {MAX_DEPTH})")
    lines = command_lines(args[0])
    _depth += 1
    try:
        for number, line in lines:
            out.say(f"spektro> {line}")
            try:
                if registry.run_command(state, line):
                    return True  # quit i filen
            except (ValueError, RuntimeError, OSError) as error:
                if getattr(error, "run_line", False):
                    raise  # redan märkt av en inre run: där står felet
                raise _with_place(error, args[0], number) from error
    finally:
        _depth -= 1
    return None


@registry.command("wait", "SEKUNDER: vänta, till exempel medan lampan blir varm (högst 600 s, Ctrl+C avbryter)",
                  "wait SEKUNDER")
def cmd_wait(state, args):
    """Kommandot wait SEKUNDER: väntar 1 till MAX_WAIT hela sekunder; Ctrl+C avbryter (main skriver Avbrutet.).

    Fel: ValueError med input.invalid_argument om SEKUNDER inte är ett heltal från 1 till MAX_WAIT.
    """
    registry.need(args, ("SEKUNDER",), "wait")
    seconds = registry.to_int("SEKUNDER", args[0], 1)
    if seconds > MAX_WAIT:
        raise ValueError(f"input.invalid_argument: SEKUNDER ska vara högst {MAX_WAIT}")
    out.say(f"väntar {seconds} s")
    time.sleep(seconds)
