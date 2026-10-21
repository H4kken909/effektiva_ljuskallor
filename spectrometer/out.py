"""All utskrift till terminalen går genom den här modulen; ingen annan modul i paketet anropar print.

Texten är exakt som förut, så Adrians facit är oförändrat. Färg (rich) bara i en riktig terminal, se FARG.
"""

import os
import sys
import time

# Färg bara när både in- och utmatning är en terminal och NO_COLOR saknas. Pipat (facit, tester) blir det print som förut.
FARG = sys.stdin.isatty() and sys.stdout.isatty() and "NO_COLOR" not in os.environ
STIL = {"ok": "green", "info": "blue", "run": "cyan", "warn": "yellow", "error": "bold red", "prompt": "cyan",
        "idle": "dim", "running": "green"}

if FARG:
    try:
        from rich.console import Console
        from rich.live import Live
        from rich.progress import track
        from rich.table import Table
        from rich.text import Text
    except ImportError:  # rich saknas (kör pip install -r requirements.txt): vanlig text som förut
        FARG = False
    else:
        _konsol = Console(highlight=False)


def say(text="", stil=None):
    """Skriv en rad; i terminal med färgen stil (en nyckel i STIL), annars exakt texten."""
    _stop_live()
    if FARG and stil:
        _konsol.print(Text(str(text), style=STIL[stil]), soft_wrap=True)
    else:
        print(text)


def error(text):
    """Felrad: Fel: <text>, röd i terminal."""
    say(f"Fel: {text}", "error")


def warn(text):
    """Varningsrad: Varning: <text>, gul i terminal."""
    say(f"Varning: {text}", "warn")

def ask(prompt):
    """Läs en rad efter prompten (input skriver prompten); prompten cyan i terminal."""
    _stop_live()
    if not FARG:
        return input(prompt)
    if "readline" in sys.modules:  # readline måste få prompten själv, annars skriver pil upp över den
        return input(f"\001\033[36m\002{prompt}\001\033[0m\002")
    return _konsol.input(Text(prompt, style=STIL["prompt"]))


def fmt(x):
    """Ett tal i utskriften, som f"{x:g}" (högst sex värdesiffror). Ett ställe att ändra talformatet på."""
    return f"{x:g}"


def progress(items, text):
    """Går igenom items; i terminal med en förloppsrad (rich.progress) som försvinner när den är klar."""
    if not FARG:
        return items
    _stop_live()
    return track(items, description=text, console=_konsol, transient=True, auto_refresh=False)


def table(rows, sep):
    """Rader med två kolumner: i terminal en rich-tabell, annars varje rad som vänster + sep + höger (som förut)."""
    if not FARG:
        for left, right in rows:
            say(f"{left}{sep}{right}")
        return
    grid = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
    grid.add_column(style=STIL["run"], no_wrap=True)
    grid.add_column()
    for left, right in rows:
        grid.add_row(Text(str(left)), Text(str(right)))  # Text: hakparenteser som [ja] är text, inte rich-markup
    _konsol.print(grid)


_status = None  # statusraden som sist skrevs ovanför prompten
_live = None  # rich.live.Live medan start skriver om sin rad, annars None
_live_tid = 0.0  # när live-raden sist ritades om (time.perf_counter)


def status(text):
    """Statusraden ovanför prompten: grå, bara i terminal och bara när den ändrats sedan sist."""
    global _status
    if FARG and text != _status:
        _status = text
        _konsol.print(Text(text, style=STIL["idle"]), soft_wrap=True)


def live_line(text):
    """En rad som skrivs om på sin plats under start (rich.live), högst 10 gånger per sekund; bara i terminal."""
    global _live, _live_tid
    if not FARG:
        return
    now = time.perf_counter()
    if _live is not None and now - _live_tid < 0.1:
        return
    _live_tid = now
    if _live is None:
        _live = Live(console=_konsol, auto_refresh=False, redirect_stdout=False, redirect_stderr=False)
        _live.start()
    _live.update(Text(text, style=STIL["running"]), refresh=True)


def _stop_live():
    """Stäng live-raden innan något annat skrivs; raden står kvar med sista läget."""
    global _live
    if _live is not None:
        _live.stop()
        _live = None


def say_all(lines):
    """Skriver raderna i ordning; en rad som börjar med "Varning: " skrivs med warn (gul i terminal)."""
    for line in lines:
        if line.startswith("Varning: "):
            warn(line.removeprefix("Varning: "))
        else:
            say(line)


def pm(value, uncertainty, unit=""):
    """value ± uncertainty med 1–2 värdesiffror i osäkerheten och värdet avrundat till samma decimal (RAP-14). 1.2.14.

    Två värdesiffror när osäkerheten börjar på 1 eller 2 (0.012, 0.25), annars en (0.3, 0.008). Saknas osäkerheten
    (NaN, oändlig eller 0) blir det bara värdet, som fmt. Exempel: pm(2.25376, 0.00274, "eV") ger "2.2538 ± 0.0027 eV",
    pm(546.07, 0.4, "nm") ger "546.1 ± 0.4 nm" och pm(1234.5, 37) ger "1230 ± 40".
    """
    tail = f" {unit}" if unit else ""
    if not 0 < uncertainty < float("inf") or not abs(value) < float("inf"):
        return f"{fmt(value)}{tail}"
    mantissa, exponent = f"{uncertainty:e}".split("e")
    decimals = (2 if mantissa[0] in "12" else 1) - 1 - int(exponent)
    if decimals > 0:
        return f"{value:.{decimals}f} ± {uncertainty:.{decimals}f}{tail}"
    return f"{round(value, decimals):.0f} ± {round(uncertainty, decimals):.0f}{tail}"
