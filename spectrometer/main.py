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


START_FILE = "spektro-start.txt"  # körs före första prompten när den finns i arbetsmappen och stdin är en terminal


def start_files(kor):
    """Kommandofilerna före första prompten: spektro-start.txt (i en terminal, om den finns), sedan --kor FIL."""
    paths = [START_FILE] if sys.stdin.isatty() and Path(START_FILE).is_file() else []
    return paths + ([kor] if kor is not None else [])


def run_at_start(state, path):
    """Kör kommandofilen path med run före första prompten. Ger (quit, fel): om filen körde quit, om en rad gav Fel:."""
    out.say(f"Kör {path}")
    try:
        return bool(registry.lookup("run").run(state, [path])), False
    except (ValueError, RuntimeError, OSError) as error:
        out.error(error)
        return False, True
    except KeyboardInterrupt:
        out.say("Avbrutet.")
        return False, True


def main(argv=None):
    """Kör prompten spektro> tills quit, Ctrl+D eller Ctrl+C vid prompten; ett fel blir en rad Fel:.

    Med en sökväg efter kommandot mäts bara den bildfilen en gång (run_file). Flaggorna (-h visar dem): --version,
    --kor FIL [--avsluta], --camera N, --input PATH, --output DIR. Med --avsluta: 1 om en rad i filen gav Fel:, annars 0;
    argparse ger 2 vid en felaktig flagga. argv: orden efter programnamnet, None läser sys.argv.
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
    parser.add_argument("--version", action="version", version=f"spektro {__version__}", help="skriv versionen och avsluta")
    parser.add_argument("--kor", metavar="FIL", help="kör kommandofilen FIL (som run FIL) före första prompten")
    parser.add_argument("--avsluta", action="store_true", help="med --kor: avsluta efter filen, slutkod 0 eller 1")
    where = parser.add_mutually_exclusive_group()
    where.add_argument("--camera", type=int, metavar="N", help="källan är kamera N (som source camera N)")
    where.add_argument("--input", metavar="PATH", help="källan är bildfilen PATH (som source file PATH)")
    parser.add_argument("--output", metavar="DIR", help="mappen för mätmapparna (output_dir, annars data)")
    args = parser.parse_args(argv)
    if args.avsluta and args.kor is None:
        parser.error("--avsluta kräver --kor FIL")
    registry.load(commands.modules())
    state = session.new_state(session.DEFAULTS)
    if args.camera is not None:
        state["settings"]["source"] = ("camera", args.camera)
    if args.input is not None:
        state["settings"]["source"] = ("file", args.input)
    if args.output is not None:
        state["settings"]["output_dir"] = args.output
    if args.path is not None:
        return run_file(state, args.path)
    if not args.avsluta:
        out.say("Skriv help för kommandona. quit eller Ctrl+D avslutar.")
    failed = False
    quit_now = False
    for path in start_files(args.kor):
        quit_now, error = run_at_start(state, path)
        failed = failed or error
        if quit_now:
            break
    if args.avsluta or quit_now:
        return 1 if failed else 0
    while True:
        try:
            line = out.ask("spektro> ")
        except (EOFError, KeyboardInterrupt):
            out.say()
            break
        try:
            if registry.run_line(state, line):  # som run_command, och raden hamnar i history och undo
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
