import os
import re
import sys
import time

import numpy as np

try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:
    tk = None

from spectrometer import __version__
from spectrometer.core import out, registry
from spectrometer.live import live
from spectrometer.measurement import calc, measure, source
from spectrometer.visual import display, highlight, plot, theme, viewfile

PLAIN = str.maketrans({"❯": ">", "✓": "+", "▲": "!", "≠": "!=", "○": "o", "●": "*", "‖": "||", "–": "-", "›": ">",
                       "│": "|", "◀": "<"})
STYLES = {"ok": "ok", "info": "star", "run": "purple", "warn": "amber", "error": "red", "prompt": "prompt",
          "idle": "comment", "running": "ok", "cmd": "cmd", "out": "text", "note": "label",
          "table": "text", "stale": "text"}
HIGHLIGHT = {"path": "star", "wave": "pink", "num": "violet", "unit": "comment", "ok": "mint", "warn": "amber",
             "bad": "red", "name": "purple"}
ANSI_COLORS = ["comment", "red", "green", "yellow", "blue", "purple", "teal", "text"]
BLOCKS = ("prism", "yellow", "logo", "team")
FIRST_HINT = ("Only the terminal is shown. view spectrum on shows the curve, view camera on the camera image "
              "(view lists all panes).")
HELLO = f"spektro {__version__}. Type help for the commands, start for live, quit exits.\n\n"


def wanted(args_terminal=False, forced=False):
    if tk is None:
        return False
    return forced or (not args_terminal and not os.environ.get("SPEKTRO_TERMINAL")
                      and out.tty(sys.stdin) and out.tty(sys.__stdout__))


def open_window(state):
    if tk is None:
        return None, "tkinter is missing (python check_install.py says how to install it)"
    if sys.platform == "win32":
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    try:
        root = tk.Tk(className="spektro")
    except tk.TclError as error:
        return None, f"no window can be opened ({error})"
    return Window(state, root), None


def show(widget, visible, **where):
    if visible:
        widget.grid(**where)
    else:
        widget.grid_remove()


class Window:
    def __init__(self, state, root):
        self.state = state
        self.root = root
        self.acq = self.until = self.waiting = None
        self.drawn_view = self.saved = self.tick_error = None
        self.parts = None
        self.prompt_shown = self.closing = self.splashing = self.dropped = self.hidden = self.typed = False
        self.relayout = None
        self.shown = self.draws = 0
        self.last_full = -1.0
        self.next_draw = self.last_chrome = 0.0
        self.rates = (live.Rate(), live.Rate())
        self.jobs = []
        colors = self.colors = theme.DARK
        root.title(f"spektro {__version__}")
        width, height = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{int(width * 0.9)}x{int(height * 0.88)}+{int(width * 0.05)}+{int(height * 0.03)}")
        root.minsize(700, 450)
        root.columnconfigure(0, weight=1)
        root.configure(bg=colors["bg"])
        self.k = k = root.winfo_fpixels("1i") / 96
        try:
            self.plain = root.tk.call("::tk::pkgconfig", "get", "fontsystem") == "x11"
        except tk.TclError:
            self.plain = False
        families = tkfont.families(root)
        family = next((name for name in theme.MONO_FONTS if name in families),
                      tkfont.nametofont("TkFixedFont", root=root).cget("family"))
        size = 11 if sys.platform == "win32" else 10
        self.font = tkfont.Font(root=root, family=family, size=size)
        self.font_bold = tkfont.Font(root=root, family=family, size=size, weight="bold")
        self.small = tkfont.Font(root=root, family=family, size=9)
        self.small_bold = tkfont.Font(root=root, family=family, size=9, weight="bold")
        self.chain = tk.Canvas(root, height=int(36 * k), bd=0, highlightthickness=0, bg=colors["bg_dark"])
        self.hairs = [tk.Frame(root, height=max(1, round(k)), bd=0, bg=colors["hair"]) for _ in range(3)]
        self.console = console = tk.Text(root, wrap="char", font=self.font, height=12, bd=0, highlightthickness=0,
                                         padx=int(12 * k), pady=int(6 * k), insertwidth=max(2, round(2 * k)),
                                         undo=False, blockcursor=True, bg=colors["pane"], fg=colors["cmd"],
                                         insertbackground=colors["pink"], selectbackground=colors["select"],
                                         selectforeground=colors["cmd"], inactiveselectbackground=colors["select"])
        for name, gravity in (("pstart", "right"), ("input", "left"), ("splash_end", "left")):
            console.mark_set(name, "1.0")
            console.mark_gravity(name, gravity)
        self.figure_box = tk.Frame(root, bd=0, highlightthickness=0, bg=colors["bg"])
        self.win = plot.embed(self.figure_box)
        self.win["widget"].configure(highlightthickness=0, bd=0, bg=colors["bg"])
        self.win["widget"].pack(fill="both", expand=True)
        plot.enable_blit(self.win)
        self.win["camera_every"] = 1 / live.CAMERA_RATE
        self.win["camera_look"] = source.bloom
        self.status = tk.Canvas(root, height=int(30 * k), bd=0, highlightthickness=0, bg=colors["bg_dark"])
        self.panel = tk.Text(root, width=34, font=self.small, bd=0, highlightthickness=0, padx=10, pady=8,
                             state="disabled", wrap="none", bg=colors["bg_dark"], fg=colors["text"])
        console.bind("<Key>", self.key)
        console.bind("<KeyRelease>", self.tint_input)
        console.bind("<<Paste>>", self.paste)
        console.bind("<<Cut>>", lambda event: "break")
        self.chain.bind("<Configure>", self.update_bars)
        self.status.bind("<Configure>", self.update_bars)
        root.protocol("WM_DELETE_WINDOW", self.close_button)
        root.bind("<Map>", self.ready)
        console.bind("<Configure>", self.console_resized, add="+")
        for tag, key in STYLES.items():
            console.tag_configure(tag, foreground=colors[key])
        for tag, key in HIGHLIGHT.items():
            console.tag_configure(f"hl_{tag}", foreground=colors[key], underline=tag == "path")
        console.tag_configure("prompt", font=self.font_bold)
        console.tag_configure("cmdword", foreground=colors["purple"], font=self.font_bold)
        self._layout()

    def ready(self, event):
        marker = os.environ.get("SPEKTRO_READY")
        if marker and event.widget is self.root:
            open(marker, "w", encoding="utf-8").write("ok")

    def _layout(self):
        view = self.state["view"]
        rows = [row for row, key in (("camera", "camera"), ("strip", "roi"), ("curve", "spectrum")) if view[key]]
        if self.splashing:
            rows = []
        full = view["camera_view"] == "full"
        if tuple(rows) != self.win["rows"] or full != self.win.get("placed_full", False):
            self.win["view"] = view
            plot.place(self.win, rows)
        rail, figure, status = view["rail"], bool(rows), view["status"]
        panel = view["panel"] and not self.splashing
        both = {"column": 0, "columnspan": 2, "sticky": "ew"}
        show(self.chain, rail, row=0, **both)
        show(self.hairs[0], rail, row=1, **both)
        show(self.hairs[1], figure, row=3, **both)
        show(self.figure_box, figure, row=4, column=0, sticky="nsew")
        show(self.panel, panel, row=4 if figure else 2, column=1, sticky="ns")
        show(self.hairs[2], status, row=5, **both)
        show(self.status, status, row=6, **both)
        self.console.grid(row=2, column=0, columnspan=1 if panel and not figure else 2, sticky="nsew")
        self.root.rowconfigure(2, weight=0 if figure else 1)
        self.root.rowconfigure(4, weight=1 if figure else 0)
        self.last_full = -1.0
        self.drawn_view = None

    def write(self, text, style=None):
        kind, head = style if isinstance(style, tuple) else (style, 0)
        tag = kind if kind in STYLES else "out"
        if kind in ("warn", "error"):
            text = f"{self.text('▲')} {text}"
        parts = []
        if head:
            parts += [self.text(text[:head]), (tag, "hl_name")]
        for chunk, mark in highlight.segments(text[head:], kind):
            parts += [self.text(chunk), (tag, f"hl_{mark}") if mark else tag]
        self.console.insert("pstart" if self.prompt_shown else "end-1c", *parts)
        self.console.see("end")
        self.root.update_idletasks()

    def text(self, text):
        return text.translate(PLAIN) if self.plain else text

    def show_prompt(self, text=None):
        console = self.console
        if console.get("end-2c") not in ("\n", ""):
            console.insert("end-1c", "\n")
        start = console.index("end-1c")
        console.insert("end-1c", text or self.text("❯ "), "prompt")
        console.mark_set("pstart", start)
        console.mark_set("input", "end-1c")
        console.mark_set("insert", "end-1c")
        console.see("end")
        self.prompt_shown = True
        if self.hidden:
            self.cursor(True)

    def ask(self, prompt):
        self.show_prompt(prompt)
        self.waiting = tk.StringVar(master=self.root)
        self.console.focus_set()
        self.root.wait_variable(self.waiting)
        answer = self.waiting.get()
        self.waiting = None
        return answer

    def _line(self):
        return self.console.get("input", "end-1c")

    def _set_line(self, text):
        self.console.delete("input", "end-1c")
        self.console.insert("end-1c", text)
        self.console.mark_set("insert", "end-1c")

    def key(self, event):
        console = self.console
        key = event.keysym
        ctrl = event.state & 4
        if self.splashing:
            if not key.endswith(("_L", "_R", "_Lock")) and key != "ISO_Level3_Shift":
                self.skip_splash()
            return "break"
        if ctrl and key.lower() == "c":
            if console.tag_ranges("sel"):
                return None
            self.ctrl_c()
            return "break"
        if not self.prompt_shown:
            return "break" if (event.char or key in ("BackSpace", "Delete", "Return")) else None
        if key in ("Return", "KP_Enter"):
            self._enter()
            return "break"
        selected = console.tag_ranges("sel")
        if key in ("BackSpace", "Left") and console.compare("insert", "<=", "input") and not selected:
            return "break"
        if (event.char or key in ("BackSpace", "Delete")) and not ctrl:
            if selected and console.compare("sel.first", "<", "input"):
                console.tag_remove("sel", "1.0", "end")
            if console.compare("insert", "<", "input"):
                console.mark_set("insert", "end-1c")
        return None

    def paste(self, event):
        self.console.mark_set("insert", "end-1c")

    def ctrl_c(self):
        if self.acq is not None:
            self.stop_live()
        elif self.prompt_shown and self.waiting is None:
            self.console.insert("end-1c", "^C")
            self.prompt_shown = False
            self.show_prompt()

    def tint_input(self, event=None):
        if not self.prompt_shown or self.waiting is not None:
            return
        self.console.tag_remove("cmdword", "input", "end")
        word = re.match(r"\s*(\S+)", self._line())
        if word:
            self.console.tag_add("cmdword", f"input+{word.start(1)}c", f"input+{word.end(1)}c")

    def _enter(self):
        self.tint_input()
        line = self._line()
        self.console.insert("end-1c", "\n")
        self.prompt_shown = False
        self.typed = True
        if self.waiting is not None:
            self.waiting.set(line)
            return
        self.execute(line)
        if not self.closing:
            self.show_prompt()

    def execute(self, line):
        words = line.lower().split()
        if words and words[0] == "stop":
            if self.acq is None:
                out.say("live is not running. start starts live.")
            self.stop_live()
            return
        source_before = self.state["settings"]["source"]
        acq = self.acq
        if acq is not None:
            acq.take()
        result = None
        try:
            result = registry.run_command(self.state, line)
        except (ValueError, RuntimeError, OSError) as error:
            out.error(error)
        except Exception as error:
            out.error(f"unexpected error ({type(error).__name__}: {error})")
        finally:
            if self.acq is not None and self.state["settings"]["source"] != source_before:
                live.switch_source(self.state, self.acq, source_before)
            if acq is not None:
                acq.lock.release()
        if result is True:
            self.close()
            return
        self.win.update(display.window_info(self.state))
        self.win["foot"] = None
        view = self.state["view"]
        if viewfile.pick(view) != self.saved:
            self.saved = viewfile.pick(view)
            viewfile.save(view)
        self._layout()
        self.update_bars()
        if self.acq is not None:
            self.acq.go.set()

    def start_live(self, seconds):
        if self.acq is not None:
            raise ValueError("live is already running. Type stop to end live.")
        kind, value = self.state["settings"]["source"]
        src = source.open_source(kind, value)
        try:
            measure.apply_controls(self.state, src)
        except BaseException:
            source.close_source(src)
            raise
        measure.lend(self.state["settings"]["source"], src)
        self.switch = sys.getswitchinterval()
        sys.setswitchinterval(live.SWITCH_INTERVAL)
        self.acq = live.Acquisition(self.state, src)
        self.acq.start()
        self.until = None if seconds is None else time.perf_counter() + seconds
        self.rates = (live.Rate(), live.Rate())
        self.last_full = -1.0
        out.say("Live. Type commands as usual; stop or Ctrl+C ends live.")
        if not self.state["view"]["spectrum"]:
            out.say("the curve is hidden: view spectrum on")

    def stop_live(self):
        if self.acq is None:
            return
        acq, self.acq = self.acq, None
        acq.stop()
        sys.setswitchinterval(self.switch)
        measure.lend(None, None)
        source.close_source(acq.src)
        self.drawn_view = None
        out.say("live stopped")

    def show_latest(self):
        self.drawn_view = None

    def tick(self):
        if self.closing:
            return
        try:
            self._tick()
        except Exception as error:
            if str(error) != self.tick_error:
                out.error(f"unexpected error in the window ({type(error).__name__}: {error})")
                self.tick_error = str(error)
        if not self.closing:
            wait = 5 if self.acq is None else max(1, min(5, int((self.next_draw - time.perf_counter()) * 1000)))
            self.root.after(wait, self.tick)

    def _tick(self):
        now = time.perf_counter()
        if self.acq is not None and self.until is not None and now >= self.until:
            self.stop_live()
        acq = self.acq
        if acq is not None:
            error, acq.error = acq.error, None
            if isinstance(error, RuntimeError):
                out.error(error)
                self.stop_live()
                acq = None
            elif error is not None:
                out.error(f"{error}  (the measurement is paused: fix it with a command, or type stop)")
                self.last_full = -1.0
        if acq is not None:
            self._draw_live(acq, now)
        else:
            self._draw_still(now)
        if now - self.last_chrome >= 0.5:
            self.update_bars()

    def _draw_live(self, acq, now):
        if now < self.next_draw:
            return
        locked = acq.take(0.004)
        try:
            latest = acq.latest
            measured = self.rates[0].add(acq.count, now)
            drawn = self.rates[1].add(self.draws, now)
            full = now - self.last_full >= 1.0
            if latest is None or (latest[0] == self.shown and not full):
                return
            _number, spectrum, values = latest
            if full:
                self.win.update(display.frame_info(self.state, self.win, spectrum, values, (measured, drawn)))
                self.win["foot"] = None
                if not acq.go.is_set():
                    self.win["warn"] = "MEASUREMENT PAUSED - see the terminal"
                self.last_full = now
            self.shown = latest[0]
            period = 1 / live.DRAW_RATE
            self.next_draw = max(self.next_draw, now - period) + period
            if not self.win["rows"]:
                return
            self.win["image"] = self.state["image"]
            if display.draw_spectrum(self.state, self.win, spectrum, values, live=full) == "full":
                self.root.update_idletasks()
            self.draws += 1
        finally:
            if locked:
                acq.lock.release()

    def _draw_still(self, now):
        spectrum = self.state["spectrum"]
        view = self.state["view"]
        view_key = (id(spectrum), tuple(self.win["rows"]), view["normalize"], view["glow"])
        if view_key == self.drawn_view and now - self.last_full < 2.0:
            return
        self.drawn_view = view_key
        self.last_full = now
        if not self.win["rows"]:
            return
        if spectrum is None:
            self.win["fig"].canvas.draw_idle()
            return
        values = calc.masked_values(spectrum)
        self.win.update(display.frame_info(self.state, self.win, spectrum, values))
        self.win["foot"] = None
        self.win["image"] = self.state["image"]
        self.win["camera_time"] = -1.0
        display.draw_spectrum(self.state, self.win, spectrum, values, live=True)

    def update_bars(self, event=None):
        if self.closing or self.splashing:
            return
        now = self.last_chrome = time.perf_counter()
        acq = self.acq
        timing = acq.timing if acq is not None else {}
        spectrum = self.state["spectrum"]
        stats = {"live": acq is not None,
                 "measured": self.rates[0].add(acq.count, now) if acq is not None else 0.0,
                 "drawn": self.rates[1].add(self.draws, now) if acq is not None else 0.0,
                 "read_ms": timing["read"] * 1000 if "read" in timing else None,
                 "compute_ms": timing["compute"] * 1000 if "compute" in timing else None,
                 "camera": spectrum.get("camera") if spectrum is not None else None,
                 "warn": self.win.get("warn")}
        view = self.state["view"]
        if view["rail"]:
            self.draw_chain(*display.chain_stages(self.state, stats))
        if view["status"]:
            self.draw_status(*display.status_line(self.state, stats))
        if view["panel"]:
            self.panel.configure(state="normal")
            self.panel.delete("1.0", "end")
            self.panel.insert("1.0", "\n".join(display.info_lines(self.state, stats)))
            self.panel.configure(state="disabled")

    def draw_chain(self, stages, hint):
        canvas = self.chain
        c, k = self.colors, self.k
        canvas.delete("all")
        height = canvas.winfo_height()
        mid = height / 2
        x = 16 * k
        gap = 12 * k
        for i, (text, kind) in enumerate(stages):
            text = self.text(text)
            font = self.small_bold if kind == "stale" else self.small
            width = font.measure(text)
            if kind == "stale":
                x0, x1 = x - 14 * k, x + width + 12 * k
                top, bottom, notch = 7 * k, height - 7 * k, 8 * k
                self.glow = glow_image(self.root, x1 - x0, height, top, bottom, notch, 5 * k, c["red"], c["bg_dark"])
                canvas.create_image(x0 - round(15 * k), 0, image=self.glow, anchor="nw")
                canvas.create_polygon((x0, top, x1, top, x1 + notch, mid, x1, bottom, x0, bottom, x0 + notch, mid),
                                      fill=c["red"], outline="")
                canvas.create_text(x, mid, text=text, anchor="w", font=font, fill=c["bg_dark"])
            else:
                head_color = {"done": c["mint"], "live": c["pink"], "off": c["faint"]}.get(kind, c["comment"])
                rest_color = {"done": c["label"], "live": c["fg"], "off": c["faint"]}.get(kind, c["comment"])
                canvas.create_text(x, mid, text=text[:1], anchor="w", font=font, fill=head_color)
                canvas.create_text(x + font.measure(text[:1]), mid, text=text[1:], anchor="w", font=font,
                                   fill=rest_color)
            x += width + gap
            if i < len(stages) - 1:
                if kind != "stale" and stages[i + 1][1] != "stale":
                    canvas.create_line(x, mid - 5 * k, x + 4 * k, mid, x, mid + 5 * k, fill=c["gutter"],
                                       width=max(1, round(k)))
                x += 4 * k + gap
        right = canvas.winfo_width() - 16 * k
        lead = self.text("› next: ")
        fits = canvas.winfo_width() <= 1 or x + self.small.measure(lead) + self.small_bold.measure(hint or "") <= right
        if hint and fits:
            canvas.create_text(right, mid, text=hint, anchor="e", font=self.small_bold, fill=c["pink"])
            canvas.create_text(right - self.small_bold.measure(hint), mid, text=lead, anchor="e", font=self.small,
                               fill=c["comment"])

    def draw_status(self, left, right):
        canvas = self.status
        c, k = self.colors, self.k
        canvas.delete("all")
        mid = canvas.winfo_height() / 2
        left, right = self.text(left), [(self.text(text), kind) for text, kind in right]
        colors = {"label": c["comment"], "value": c["value"], "sep": c["gutter"], "warn": c["amber"]}
        x = canvas.winfo_width() - 12 * k - sum(self.small.measure(text) for text, _kind in right)
        if canvas.winfo_width() <= 1 or 12 * k + self.small.measure(left) + 24 * k <= x:
            canvas.create_text(12 * k, mid, text=left, anchor="w", font=self.small, fill=c["label"])
        for text, kind in right:
            canvas.create_text(x, mid, text=text, anchor="w", font=self.small, fill=colors[kind])
            x += self.small.measure(text)

    def run(self, paths, splash=None, delay=None):
        out.set_sink(self)
        live.HOST = self
        try:
            self.splashing = splash is not None
            values, self.first = viewfile.load()
            self.paths = paths
            self.state["view"].update(values)
            self.saved = viewfile.pick(self.state["view"])
            self._layout()
            self.win.update(display.window_info(self.state))
            self.win["foot"] = None
            self.console.focus_set()
            if splash is None:
                self.write(HELLO)
                self.root.after_idle(self.after_splash)
            else:
                self.cursor(False)
                self.root.update()
                self.begin_splash(splash, delay)
            self.root.mainloop()
        finally:
            self.stop_splash()
            self.stop_live()
            live.HOST = None
            out.set_sink(None)
            self.root.destroy()
        return 0

    def after_splash(self):
        if self.first:
            self.write(FIRST_HINT + "\n", "info")
        for path in self.paths:
            self.write(f"Running {path}\n")
            self.execute(f'run "{path}"')
            if self.closing:
                return
        self.show_prompt()
        self.root.after(5, self.tick)

    def begin_splash(self, splash, delay):
        self.make = splash
        self.after_rows = (-(-len(FIRST_HINT) // self._console_size()[0]) if self.first else 0) + 1
        self.splash_layout()
        self.shown_blocks = set()
        self.console.mark_gravity("splash_end", "right")
        pause = dict(self.parts["pauses"])
        if delay is not None:
            pause.update(dict.fromkeys(BLOCKS, max(0.0, delay)))
        before, wait = "start", 0.0
        for name in BLOCKS:
            if self.parts[name]:
                wait += pause.get(before, 0.6)
                self.jobs.append(self.root.after(round(wait * 1000), self.show_block, name))
                before = name
        wait += pause.get(before, 0.6)
        self.jobs.append(self.root.after(round(wait * 1000), self.end_splash))

    def stop_splash(self):
        for job in self.jobs:
            self.root.after_cancel(job)
        self.jobs = []

    def splash_layout(self):
        columns, rows, aspect = self._console_size()
        if self.parts is not None and self.size == (columns, rows):
            return False
        self.size = (columns, rows)
        self.parts = self.make(columns, rows, aspect=aspect, after=self.after_rows)
        return True

    def console_resized(self, event):
        if self.parts is None or self.typed:
            return
        if self.relayout is not None:
            self.root.after_cancel(self.relayout)
        self.relayout = self.root.after(120, self.relayout_splash)

    def relayout_splash(self):
        self.relayout = None
        if not self.typed and self.splash_layout():
            self.render_splash()

    def show_block(self, name):
        self.shown_blocks.add(name)
        self.render_splash()

    def skip_splash(self):
        self.stop_splash()
        self.shown_blocks = set(BLOCKS)
        self.render_splash()
        self.end_splash()

    def end_splash(self):
        self.splashing = False
        self.console.mark_gravity("splash_end", "left")
        self._layout()
        if self.win["rows"] and int(self.console.index("splash_end").split(".")[0]) + 1 > 12:
            self.dropped = True
            self.shown_blocks -= {"prism", "logo"}
            self.render_splash()
        self.after_splash()

    def ansi_pieces(self, text):
        pieces, color, bold = [], None, False
        for i, part in enumerate(re.split(r"\x1b\[([0-9;]*)m", text)):
            if i % 2 == 0:
                if part:
                    tag = f"ansi{color}{'-b' if bold else ''}"
                    self.console.tag_configure(tag, foreground=color or self.colors["text"],
                                               font=self.font_bold if bold else self.font)
                    pieces.append((self.text(part), tag))
                continue
            codes = [int(code or 0) for code in part.split(";")]
            while codes:
                code = codes.pop(0)
                if code == 0:
                    color, bold = None, False
                elif code == 1:
                    bold = True
                elif code == 22:
                    bold = False
                elif 30 <= code <= 37:
                    color = self.colors[ANSI_COLORS[code - 30]]
                elif code == 38:
                    color = "#" + "".join(f"{min(255, round(value / 16) * 16):02x}" for value in codes[1:4])
                    del codes[:4]
        return pieces

    def render_splash(self):
        cut = self.parts["left"] + self.parts["width"]
        pieces = []
        for name in BLOCKS:
            if name in self.shown_blocks:
                for row, col, text in self.parts[name]:
                    pieces.append((row, col, self.ansi_pieces(text), cut if name == "prism" else None))
        pieces.sort(key=lambda piece: piece[:2])
        lines = {}
        done = {}
        for row, col, runs, stop in pieces:
            line = lines.setdefault(row, [])
            length = done.get(row, 0)
            if col > length:
                line += [" " * (col - length), ()]
                length = col
            for text, tag in runs:
                if stop is not None:
                    text = text[:max(0, stop - length)]
                if text:
                    line += [text, tag]
                    length += len(text)
            done[row] = length
        first = min(lines) if lines and self.dropped else 0
        last = max(lines) if lines else -1
        args = []
        for row in range(first, last + 1):
            args += lines.get(row, []) + ["\n", ()]
        self.console.delete("1.0", "splash_end")
        if args:
            self.console.insert("1.0", *args)
        self.console.mark_set("splash_end", f"{last - first + 2}.0")
        self.console.see("end")

    def cursor(self, visible):
        self.hidden = not visible
        width = max(2, round(2 * self.k)) if visible else 0
        self.console.configure(insertontime=600 if visible else 0, insertwidth=width, blockcursor=visible,
                               insertbackground=self.colors["pink" if visible else "pane"])

    def _console_size(self):
        cell_w = self.font.measure("M")
        cell_h = self.font.metrics("linespace")
        padx, pady = int(self.console.cget("padx")), int(self.console.cget("pady"))
        columns = max(20, (self.console.winfo_width() - 2 * padx) // cell_w)
        rows = max(5, (self.console.winfo_height() - 2 * pady) // cell_h)
        return columns, rows, cell_h / cell_w

    def close_button(self):
        if self.splashing:
            self.close()
        elif self.waiting is not None:
            self.waiting.set("")
        else:
            self._set_line("quit")
            self._enter()

    def close(self):
        self.closing = True
        self.stop_live()
        self.root.quit()


def glow_image(root, width, height, top, bottom, notch, sigma, color, background):
    pad = round(3 * sigma)
    w, h = round(width + notch) + 2 * pad + 1, int(height)
    xs = np.arange(w) - pad + 0.5
    ys = np.arange(h) + 0.5
    slope = notch * (1 - np.abs(ys - height / 2) / max(height / 2 - top, 1.0))
    inside = ((ys[:, None] >= top) & (ys[:, None] <= bottom) & (xs[None, :] >= slope[:, None])
              & (xs[None, :] <= width + slope[:, None]))
    taps = np.arange(-pad, pad + 1)
    kernel = np.exp(-taps ** 2 / (2 * sigma ** 2))
    kernel /= kernel.sum()
    blur = np.apply_along_axis(np.convolve, 1, inside.astype(float), kernel, "same")
    blur = np.apply_along_axis(np.convolve, 0, blur, kernel, "same")
    alpha = (0.45 * blur)[..., None]
    rgb = (1 - alpha) * np.array(root.winfo_rgb(background)) / 257 + alpha * np.array(root.winfo_rgb(color)) / 257
    image = tk.PhotoImage(master=root, width=w, height=h)
    rows = ["{" + " ".join(f"#{r:02x}{g:02x}{b:02x}" for r, g, b in row) + "}" for row in np.rint(rgb).astype(int)]
    image.put(" ".join(rows))
    return image
