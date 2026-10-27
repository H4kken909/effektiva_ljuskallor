import argparse
import sys

from spectrometer import __version__, commands
from spectrometer.core import out, registry, session
from spectrometer.visual import gui, viewfile


def no_console():
    path = viewfile.log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = open(path, "a", encoding="utf-8", errors="replace", buffering=1)


def main(argv=None):
    for stream in (sys.stdout, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m spectrometer.main")
    parser.add_argument("--version", action="version", version=f"spektro {__version__}")
    parser.add_argument("--run", metavar="FILE", help="run the command file FILE before the first prompt")
    parser.add_argument("--exit", dest="exit_after", action="store_true", help="with --run: exit after the file")
    parser.add_argument("--terminal", action="store_true", help="the prompt in the terminal instead of the window")
    parser.add_argument("--gui", action="store_true", help="only the window, output goes to spektro.log")
    parser.add_argument("--no-splash", action="store_true", help="with --gui: no splash screen")
    parser.add_argument("--delay", type=float, metavar="SEC", help="with --gui: seconds between splash parts")
    if "--gui" in (sys.argv[1:] if argv is None else argv):
        no_console()
    args = parser.parse_args(argv)
    registry.load(commands.modules())
    state = session.new_state(session.DEFAULTS)
    if not args.exit_after and (args.gui or gui.wanted(args.terminal)):
        window, why = gui.open_window(state)
        if window is not None:
            parts = None
            if args.gui and not args.no_splash:
                from spectrometer.visual.splash import screen

                parts = screen.splash_parts
            return window.run([] if args.run is None else [args.run], parts, args.delay)
        out.say(f"The window does not open: {why}.")
        if args.gui:
            return 1
        out.say("The prompt runs in the terminal.")
    if not args.exit_after:
        out.say("Type help for the commands. quit or Ctrl+D exits.")
    failed = False
    quit_now = False
    if args.run is not None:
        out.say(f"Running {args.run}")
        try:
            quit_now = registry.COMMANDS["run"][1](state, [args.run])
        except Exception as error:
            out.error(error)
            failed = True
    if args.exit_after or quit_now:
        return 1 if failed else 0
    while True:
        try:
            line = out.ask("spektro> ")
        except (EOFError, KeyboardInterrupt):
            out.say()
            break
        try:
            if registry.run_command(state, line):
                break
        except KeyboardInterrupt:
            out.say("Cancelled.")
        except Exception as error:
            out.error(error)
            failed = True
    return 1 if failed and not out.tty(sys.stdin) else 0


if __name__ == "__main__":
    sys.exit(main())
