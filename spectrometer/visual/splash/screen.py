import builtins
import importlib
import io
import re
import shutil
import sys
import time

from spectrometer import __version__
from spectrometer.visual import viewfile
from spectrometer.visual.splash import prism, ylogo

VERSION = f"v{__version__}"
SPLASH_TIMES = {"start": 0.4, "prism": 0.8, "yellow": 0.8, "logo": 0.6, "team": 0.6}
TEXT = ["Inget prat", "Inget spring", "Inget fniss", "Inget alls!"]
PROJECT = "Grupp GRYb1  ·  Effektiva ljuskällor  ·  TFYY51 Ingenjörsprojekt, HT 2026"
TEAM = [
    ("Elias Holmberg", "Head of programming", True),
    ("Adrian Lindstedt", "Lab, testing and quality", True),
    ("Alan Hosseini", "Project manager", False),
    ("Isak Jansson", "Documentation lead", False),
    ("Oscar Al-Ishak", "Design and optics", False),
]
MODULES = ["numpy", "cv2", "matplotlib.pyplot", "spectrometer.measurement.calc", "spectrometer.core.files",
           "spectrometer.measurement.source", "spectrometer.visual.plot"]


def color(rgb, bold=False):
    return f"\x1b[{'1;' if bold else ''}38;2;{int(rgb[1:3], 16)};{int(rgb[3:5], 16)};{int(rgb[5:7], 16)}m"


YELLOW = "\x1b[1;33m"
BOLD = color("#e9e1f5", True)
ROLE = color("#a99bc0")
GREY = color("#6e5f86")
PINK = color("#ff2fa8", True)
RESET = "\x1b[0m"
LOGO_ROW, LOGO_EDGE = color("#a09070"), color("#807060")
ANSI_CODE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def write(text):
    sys.stdout.write(text)
    sys.stdout.flush()


def tty(stream):
    return stream is not None and stream.isatty()


def vt_windows():
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    out = k32.GetStdHandle(-11)
    layout = wintypes.DWORD()
    if k32.GetConsoleMode(out, ctypes.byref(layout)):
        k32.SetConsoleMode(out, layout.value | 0x0004)


def visible_len(text):
    return len(ANSI_CODE.sub("", text))


def logo_text(text):
    out, previous = "", None
    for char in text:
        if char != " ":
            code = LOGO_ROW if char == "8" else LOGO_EDGE
            if code != previous:
                out += code
                previous = code
        out += char
    return out + RESET


def splash_parts(columns, rows, aspect=2.1, after=2, side=True):
    project, version = f"{BOLD}{PROJECT}{RESET}", f"{GREY}Spektro {VERSION}{RESET}"
    dot = f"  {GREY}·{RESET}  "
    team = [f"{BOLD if highlight else GREY}{name:<18}{RESET} {ROLE if highlight else GREY}{duty}{RESET}"
            for name, duty, highlight in TEAM]
    tips = f"{GREY}Type {PINK}help{RESET}{GREY} for the commands, {PINK}quit{RESET}{GREY} to exit.{RESET}"
    side_column = 2 + max(len(row) for row in TEXT) + 4
    fits = columns - 1

    layouts = {"airy": 18, "tight": 14}
    if side and side_column + visible_len(project) <= fits:
        layouts["side"] = 9
    elif side and side_column + visible_len(team[0]) <= fits and 2 + visible_len(project) <= fits:
        layouts["narrow"] = 9
    heights = {name: rows - fixed - after for name, fixed in layouts.items()}
    layout = max(heights, key=heights.get)
    for name in layouts:
        if heights[name] >= 0.55 * rows:
            layout = name
            break
    highest = max(8, round((columns - 2) / (aspect * 3.4)))
    p = max(8, min(heights[layout], highest))
    width = max(24, min(columns - 2, round(p * aspect * 3.4)))
    middle = columns // 2
    left = max(0, middle - width // 2)

    col = 2 if layout in ("tight", "narrow") else side_column
    if col + visible_len(project + dot + version) <= fits:
        heading, tips_row = project + dot + version, tips
    else:
        heading, tips_row = project, tips + dot + version
    if layout == "airy":
        top, g = 1, p + 2
        t = g + 5
        team_pieces = [(t, 0, f"  {project}"), (t + 1, 0, f"  {version}")]
        team_pieces += [(t + 3 + i, 0, f"    {row}") for i, row in enumerate(team)]
        team_pieces += [(t + 9, 0, f"  {tips}"), (t + 10, 0, "")]
    elif layout == "tight":
        top, g = 0, p + 1
        t = g + 5
        team_pieces = [(t, 0, f"  {heading}")] + [(t + 1 + i, 0, f"    {row}") for i, row in enumerate(team)]
        team_pieces += [(t + 7, 0, f"  {tips_row}")]
    elif layout == "side":
        top, g = 0, p + 1
        team_pieces = [(g, side_column, heading)] + [(g + 1 + i, side_column, f"  {row}") for i, row in enumerate(team)]
        team_pieces += [(g + 7, 0, f"  {tips_row}")]
    else:
        top, g = 0, p + 2
        team_pieces = [(g - 1, 0, f"  {heading}")] + [(g + i, side_column, row) for i, row in enumerate(team)]
        team_pieces += [(g + 6, 0, f"  {tips_row}")]
    yellow_pieces = [(g + i, 0, f"  {YELLOW}{text}{RESET}") for i, text in enumerate(TEXT)]

    lines = prism.render(fits, p, aspect, apex=middle, reach=width / 2)
    area = logo_area(columns, rows, aspect, top + p + 1, yellow_pieces + team_pieces, after, middle)
    logo = []
    if area is not None:
        area = logo_between(area, team_pieces + yellow_pieces, aspect, columns)
    if area is not None:
        row0, column0, height = area
        for i, text in enumerate(ylogo.render(height, aspect)):
            if text.strip():
                logo.append((row0 + i, column0 + len(text) - len(text.lstrip()), logo_text(text.strip())))
    return {
        "width": width, "left": left,
        "prism": [(top + i, 0, line) for i, line in enumerate(lines)],
        "yellow": yellow_pieces, "logo": logo, "team": team_pieces,
        "pauses": dict(SPLASH_TIMES),
    }


def logo_between(area, pieces, aspect, columns):
    project = [(r, k + visible_len(text)) for r, k, text in pieces if PROJECT in text]
    if not project:
        return area
    top, right = project[0]
    inside = max(r for r, _k, _t in pieces) - top
    gap = 2 if inside - 4 >= 5 else 1
    height = min(area[2], inside - 2 * gap)
    if height < 5:
        return None
    row0 = top + 1 + (inside - height) // 2
    width = ylogo.width(height, aspect)
    text_end = max([k + visible_len(t) for r, k, t in pieces if row0 <= r < row0 + height and visible_len(t)], default=0)
    column = min(right + 4 - width, columns - 1 - width)
    column = max(text_end + 6, column)
    if column + width > columns - 1:
        return None
    return row0, column, height


def logo_area(columns, rows, aspect, first, pieces, after, middle):
    if rows < 30:
        return None
    shown = [(r, k, visible_len(t)) for r, k, t in pieces if visible_len(t)]
    last_text = max([r for r, _k, _n in shown], default=first)
    bottom = rows - after - 1
    for limit, smallest in ((last_text, 9), (max(bottom, last_text), 5)):
        for height in range(min(10, limit - first + 1), smallest - 1, -1):
            width = ylogo.width(height, aspect)
            candidates = list(range(first, limit - height + 2))
            if limit == last_text:
                candidates.sort(key=lambda r: (abs(2 * r + height - first - limit - 1), r))
            for row0 in candidates:
                end = max([k + n for r, k, n in shown if row0 <= r <= row0 + height - 1], default=0)
                start = end + 6 if end else 0
                if start + width - 1 <= columns - 2:
                    return row0, min(max(start, middle - width // 2), columns - 1 - width), height
    return None


def join_pieces(pieces):
    rows = {}
    for row, column, text in sorted(pieces, key=lambda piece: (piece[0], piece[1])):
        before = rows.get(row, "")
        rows[row] = before + " " * max(0, column - visible_len(before)) + text
    out = ""
    if rows:
        for row in range(max(rows) + 1):
            out += rows.get(row, "") + "\n"
    return out


def addition(before, new_pieces):
    old, new = join_pieces(before), join_pieces(before + new_pieces)
    return new[len(old):] if new.startswith(old) else new


def splash(delay, run_main):
    real_input, real_stdout = builtins.input, sys.stdout
    try:
        write("\x1b[0;37;40m\x1b[?25l\x1b[2J\x1b[3J\x1b[H")
        times = dict(SPLASH_TIMES)
        if delay is not None:
            for name in ("prism", "yellow", "logo", "team"):
                times[name] = max(0.0, float(delay))
        time.sleep(times["start"])
        columns, rows = shutil.get_terminal_size((120, 40))
        parts = splash_parts(columns, rows, side=False)
        written = parts["prism"]
        write(join_pieces(written))
        since = time.monotonic()
        for name in MODULES:
            importlib.import_module(name)
        time.sleep(max(0.0, times["prism"] - (time.monotonic() - since)))
        write(addition(written, parts["yellow"]))
        written = written + parts["yellow"]
        time.sleep(times["yellow"])
        logo_end = None
        if parts["logo"] and max(row for row, _k, _t in parts["logo"]) < rows - 1:
            write("".join(f"\x1b7\x1b[{row + 1};{column + 1}H{text}\x1b8" for row, column, text in parts["logo"]))
            logo_end = max(row for row, _k, _t in parts["logo"])
            time.sleep(times["logo"])
        text_end = max(row for row, _k, _t in written + parts["team"])
        under = "\n" * (logo_end - text_end) if logo_end is not None and logo_end > text_end else ""
        write(addition(written, parts["team"]) + under + "\n")
        time.sleep(times["team"])
        write("\x1b[?25h")

        sys.stdout = io.StringIO()

        def first_input(prompt=""):
            sys.stdout = real_stdout
            builtins.input = real_input
            return real_input(prompt)

        builtins.input = first_input
        run_main()
    finally:
        if isinstance(sys.stdout, io.StringIO):
            rest_text = sys.stdout.getvalue()
            sys.stdout = sys.__stdout__
            write(rest_text)
        write("\x1b[?25h\x1b[0m")


def setup_window(work):
    import threading

    try:
        import tkinter as tk

        root = tk.Tk(className="spektro")
    except Exception:
        return work()[0]
    log_path = viewfile.log_path()
    log = open(log_path, "rb")
    log.seek(0, 2)
    results = []
    root.title(f"spektro {VERSION}: setting up")
    root.configure(bg="#0d0a14")
    text = tk.Text(root, width=100, height=24, bg="#0d0a14", fg="#e9e1f5", bd=0, highlightthickness=0, padx=12,
                   pady=8, wrap="word", font="TkFixedFont")
    text.pack(fill="both", expand=True)
    text.insert("end", f"spektro {VERSION}: getting the program ready (first start, or requirements.txt changed). "
                       "This window closes by itself.\n\n")
    thread = threading.Thread(target=lambda: results.append(work()), daemon=True)

    def update():
        working = thread.is_alive()
        text.insert("end", log.read().decode("utf-8", errors="replace"))
        text.see("end")
        if working:
            root.after(50, update)
        elif results and results[0][0] == 0:
            root.after(500, root.destroy)
        else:
            error = results[0][1] if results else "Something went wrong (see spektro.log)."
            text.insert("end", f"\n{error}\n\nClose this window. The log: {log_path}\n")
            text.see("end")

    thread.start()
    root.after(50, update)
    root.mainloop()
    return results[0][0] if results else 1
