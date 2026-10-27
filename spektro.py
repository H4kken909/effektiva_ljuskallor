import argparse
import hashlib
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path

from spectrometer.visual import viewfile
from spectrometer.visual.splash import screen

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WINDOWS = sys.platform == "win32"
VENV_PY = VENV / ("Scripts/python.exe" if WINDOWS else "bin/python")
VENV_PYW = VENV / "Scripts/pythonw.exe" if WINDOWS else VENV_PY
REQUIREMENTS = ROOT / "requirements.txt"
MARKER = VENV / ".spektro-requirements"
NO_WINDOW = 0x08000000 if WINDOWS else 0
DETACHED = 0x00000008 | 0x00000200
BREAKAWAY = 0x01000000


def run(command):
    return subprocess.run([str(c) for c in command], capture_output=True, text=True, errors="replace", creationflags=NO_WINDOW)


def installed_ok():
    checksum = hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    return MARKER.exists() and MARKER.read_text() == checksum


def prepare_venv():
    if Path(sys.prefix).resolve() == VENV.resolve() or installed_ok():
        return
    steps = []
    if not VENV_PY.exists():
        print(f"  First start, setting up the program in {ROOT} (only this once)", flush=True)
        steps.append([sys.executable, "-m", "venv", VENV])
    print("  Installing the packages in requirements.txt ...", flush=True)
    steps.append([VENV_PY, "-m", "pip", "install", "--disable-pip-version-check", "--only-binary=:all:", "--progress-bar", "off", "-r", REQUIREMENTS])
    for command in steps:
        answer = run(command)
        if answer.returncode != 0:
            sys.exit(f"Could not set up the environment in {VENV}:\n{(answer.stdout + answer.stderr).strip()}")
    MARKER.write_text(hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest())
    print("  Ready", flush=True)


def start_window(extra):
    ready_file = viewfile.folder() / "window.ready"
    ready_file.parent.mkdir(parents=True, exist_ok=True)
    ready_file.unlink(missing_ok=True)
    command = [str(VENV_PYW), "-m", "spectrometer.main", "--gui"] + extra
    env = dict(os.environ, SPEKTRO_READY=str(ready_file))
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(ROOT), env.get("PYTHONPATH")) if p)
    quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if not WINDOWS:
        child = subprocess.Popen(command, env=env, start_new_session=True, **quiet)
    else:
        try:
            child = subprocess.Popen(command, env=env, creationflags=DETACHED | BREAKAWAY, **quiet)
        except OSError:
            child = subprocess.Popen(command, env=env, creationflags=DETACHED, **quiet)
    end = time.monotonic() + 60
    while time.monotonic() < end and not ready_file.exists() and child.poll() is None:
        time.sleep(0.05)
    ready_file.unlink(missing_ok=True)
    if child.returncode in (None, 0):
        return 0, "The window is open."
    return 1, f"The window closed at once (exit code {child.returncode}). See the log: {viewfile.log_path()}"


def own_console():
    if not WINDOWS:
        return False
    import ctypes

    pids = (ctypes.c_uint32 * 32)()
    count = ctypes.windll.kernel32.GetConsoleProcessList(pids, 32)
    return 0 < count <= 32 and all(pid in (os.getpid(), os.getppid()) for pid in pids[:count])


def pyw_start():
    try:
        prepare_venv()
    except SystemExit as end:
        return 1, str(end.code)
    print("Opening the window ...", flush=True)
    return start_window([])


def pyw_main():
    os.chdir(ROOT)
    viewfile.log_path().parent.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = open(viewfile.log_path(), "a", encoding="utf-8", errors="replace", buffering=1)
    print(f"--- Spektro.pyw {screen.VERSION} {time.strftime('%Y-%m-%d %H:%M:%S')} ({sys.executable}) ---", flush=True)
    if not installed_ok():
        return screen.setup_window(pyw_start)
    code, text = pyw_start()
    if code:
        print(text, flush=True)
        return screen.setup_window(lambda: (code, text))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="spektro", allow_abbrev=False,
                                     description="Starts the spectrometer. Other flags go to spectrometer.main.")
    parser.add_argument("--no-splash", action="store_true", help="no splash screen")
    parser.add_argument("--delay", type=float, metavar="SEC", help="seconds between the parts of the splash screen")
    args, rest = parser.parse_known_args()
    delay = None if args.delay is None else max(0.0, args.delay)
    terminal = screen.tty(sys.stdin) and screen.tty(sys.stdout)
    if WINDOWS and screen.tty(sys.stdout):
        screen.vt_windows()
    prepare_venv()
    own_terminal = os.environ.get("SPEKTRO_TERMINAL") or any(f in rest for f in ("--terminal", "--exit", "-h", "--help", "--version"))
    if terminal and not own_terminal:
        tk = run([VENV_PY, "-c", "import tkinter; r = tkinter.Tk(); r.withdraw(); r.destroy()"])
        if tk.returncode == 0:
            print("Opening the window ...", flush=True)
            extra = ["--no-splash"] if args.no_splash else []
            if delay is not None:
                extra += ["--delay", str(delay)]
            code, text = start_window(extra + rest)
            print(text if code else f"{text} The console is no longer needed. The log: {viewfile.log_path()}")
            if code and own_console():
                input("Press Enter to close.")
            sys.exit(code)
    if Path(sys.prefix).resolve() != VENV.resolve():
        child = subprocess.Popen([VENV_PY, ROOT / "spektro.py"] + sys.argv[1:])
        while True:
            try:
                sys.exit(child.wait())
            except KeyboardInterrupt:
                pass
    sys.argv = [sys.argv[0]] + rest

    def start_main():
        runpy.run_module("spectrometer.main", run_name="__main__", alter_sys=True)

    if args.no_splash or not terminal:
        start_main()
    else:
        screen.splash(delay, start_main)


if __name__ == "__main__":
    main()
