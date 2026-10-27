import threading
import time

from spectrometer.core import out
from spectrometer.measurement import calc, measure, source
from spectrometer.visual import display, plot

DRAW_RATE = 120
CAMERA_RATE = 25
HOST = None
SWITCH_INTERVAL = 0.0005


class Acquisition:
    def __init__(self, state, src):
        self.state = state
        self.src = src
        self.lock = threading.RLock()
        self.wanted = threading.Event()
        self.go = threading.Event()
        self.go.set()
        self.done = threading.Event()
        self.timing = {}
        self.latest = None
        self.count = 0
        self.error = None
        self.thread = threading.Thread(target=self._run, name="spektro-measuring", daemon=True)

    def _run(self):
        while not self.done.is_set():
            if not self.go.wait(0.05):
                continue
            if self.wanted.is_set():
                time.sleep(0.0002)
                continue
            try:
                with self.lock:
                    if self.done.is_set() or not self.go.is_set():
                        continue
                    timing = {}
                    spectrum = measure.measure(self.state, self.src, timing)
                    self.timing = timing
            except Exception as error:
                self.error = error
                self.go.clear()
                continue
            self.count += 1
            self.latest = (self.count, spectrum, calc.masked_values(spectrum))
            time.sleep(0)

    def take(self, timeout=None):
        self.wanted.set()
        try:
            return self.lock.acquire(timeout=-1 if timeout is None else timeout)
        finally:
            self.wanted.clear()

    def start(self):
        self.thread.start()

    def stop(self):
        self.done.set()
        self.go.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2)


class Rate:
    def __init__(self):
        self.samples = []

    def add(self, count, now):
        self.samples.append((now, count))
        while len(self.samples) > 2 and now - self.samples[0][0] > 1.0:
            self.samples.pop(0)
        (t0, c0), (t1, c1) = self.samples[0], self.samples[-1]
        return (c1 - c0) / (t1 - t0) if t1 > t0 else 0.0


def run(state, seconds):
    out.say("Live. Press Ctrl+C or close the window to stop.")
    src = win = None
    try:
        src = source.open_source(*state["settings"]["source"])
        measure.apply_controls(state, src)
        win = plot.open_plot()
        win.update(display.window_info(state))
        begun = time.perf_counter()
        while plot.is_open(win) and (seconds is None or time.perf_counter() - begun < seconds):
            started = time.perf_counter()
            spectrum = measure.measure(state, src)
            values = calc.masked_values(spectrum)
            win.update(display.frame_info(state, win, spectrum, values))
            display.draw_spectrum(state, win, spectrum, values)
            plot.pause(max(0.001, 0.05 - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        if src is not None:
            source.close_source(src)
        if win is not None:
            plot.close(win)
    out.say("live stopped")


def switch_source(state, acq, before):
    kind, value = state["settings"]["source"]
    try:
        new = source.open_source(kind, value)
    except (RuntimeError, ValueError) as error:
        state["settings"]["source"] = before
        out.error(f"{error}  (live keeps measuring from {before[0]} {before[1]})")
        return
    source.close_source(acq.src)
    acq.src = new
    measure.apply_controls(state, acq.src)
    measure.lend(state["settings"]["source"], acq.src)
    out.say(f"live now measures from {kind} {value}")
