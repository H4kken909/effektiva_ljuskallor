"""Startar programmet: python -m spectrometer.main ger prompten spektro>, med en bildfil mäts den en gång."""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import numpy as np

from spectrometer import (
    __version__,
    commands,
    files,
    measure,
    out,
    plot,
    registry,
    session,
)

log = logging.getLogger("spektro")


def open_log(folder="logs"):
    """Loggfilen logs/spektro.log (1 MB, tre gamla sparas); skapas först när något loggas."""
    if log.handlers:
        return
    Path(folder).mkdir(exist_ok=True)
    handler = RotatingFileHandler(Path(folder) / "spektro.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(asctime)s spektro " + __version__ + " %(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def run_file(state, path):
    """Mäter en bildfil en gång: skriver toppen, sparar mätningen och ritar spektrumet. Ger slutkoden 0 eller 1."""
    state["settings"]["source"] = ("file", path)
    try:
        spectrum = measure.measure(state)
        i = np.argmax(spectrum["values"])
        out.say(f"Topp {spectrum['values'][i]:g} vid pixel {spectrum['x'][i]:g}")
        folder = files.save_measurement(state["settings"]["output_dir"], spectrum, state["image"], state["settings"])
        out.say(f"Sparad i {folder.as_posix()}")
        win = plot.open_plot()
        masked = np.where(spectrum["mask"], spectrum["values"], np.nan)
        plot.draw(win, spectrum["x"], masked, spectrum["x_label"], spectrum["y_label"])
        plot.show()
    except (ValueError, RuntimeError, OSError) as error:
        out.error(error)
        return 1
    return 0


def main():
    """Kör prompten spektro> tills quit, Ctrl+D eller Ctrl+C vid prompten; ett fel blir en rad Fel:.

    Med en sökväg efter kommandot mäts bara den bildfilen en gång (run_file).
    Returnerar: slutkoden. Med en sökväg den från run_file. Annars 1 om något kommando gav Fel: och stdin inte är en
    terminal (en kommandofil eller ett rör), annars 0.
    """
    for stream in (sys.stdout, sys.stdin):
        if hasattr(stream, "reconfigure"):  # pytest byter ut sys.stdin mot ett objekt utan reconfigure
            stream.reconfigure(encoding="utf-8")  # samma bytes på Windows och Arch, vilken kodsida konsolen än har
    parser = argparse.ArgumentParser(
        prog="python -m spectrometer.main",
        description="Utan sökväg: prompten spektro>. Med sökväg: läser bildfilen, skriver toppen, sparar mätningen "
        "och ritar spektrumet.",
    )
    parser.add_argument("path", nargs="?", help="sökvägen till en bildfil (utan den startar prompten)")
    args = parser.parse_args()
    registry.load(commands.modules())
    state = session.new_state(session.DEFAULTS)
    if args.path is not None:
        return run_file(state, args.path)
    out.say("Skriv help för kommandona. quit eller Ctrl+D avslutar.")
    failed = False
    while True:
        try:
            line = out.ask("spektro> ")
        except (EOFError, KeyboardInterrupt):
            out.say()
            break
        try:
            if registry.run_command(state, line):
                break
        except (ValueError, RuntimeError, OSError) as error:
            out.error(error)
            failed = True
        except KeyboardInterrupt:
            out.say("Avbrutet.")
        except Exception as error:  # oväntat: en rad och loggen, aldrig ut ur programmet
            if os.environ.get("SPEKTRO_DEBUG"):
                raise  # hela tracebacken, som förut
            open_log()
            log.exception("%s", line)
            out.error(f"oväntat fel ({type(error).__name__}: {error}), detaljer i logs/spektro.log")
            failed = True
    return 1 if failed and not sys.stdin.isatty() else 0


if __name__ == "__main__":
    sys.exit(main())
