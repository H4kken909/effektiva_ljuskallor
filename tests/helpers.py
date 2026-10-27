import io
import sys

import cv2
import numpy as np
import pytest

from spectrometer.core import registry, session
from spectrometer.measurement import source
from spectrometer.visual import gui


class FakeCamera:
    def __init__(self, frames):
        self.frames = list(frames)
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        if self.released or not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True

    def set(self, prop, value):
        return True

    def get(self, prop):
        return 0.0

    def getBackendName(self):
        return "FAKE"


def use_camera(monkeypatch, frames):
    camera = FakeCamera(frames)
    monkeypatch.setattr(source.cv2, "VideoCapture", lambda index, backend: camera)
    return camera


def cameras(monkeypatch, frames):
    feed = list(frames)

    def open_camera(index, backend):
        camera = FakeCamera([])
        camera.frames = feed
        return camera

    monkeypatch.setattr(source.cv2, "VideoCapture", open_camera)


class Tty(io.StringIO):
    def isatty(self):
        return True


def terminal(monkeypatch, answers):
    asked = []
    feed = iter(answers)

    def fake_input(prompt):
        asked.append(prompt)
        return next(feed)

    monkeypatch.setattr(sys, "stdin", Tty())
    monkeypatch.setattr("builtins.input", fake_input)
    return asked


def tk_window(state):
    if gui.tk is None:
        pytest.skip("Python without Tk")
    window, why = gui.open_window(state)
    if window is None:
        pytest.skip(why)
    window.root.withdraw()
    return window


def command_file(tmp_path, text, name="file.txt"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path.as_posix()


def line_image(column=12, value=200):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, column] = value
    return image


def new_state():
    return session.new_state(session.DEFAULTS)


def transmission_state(tmp_path):
    cv2.imwrite(str(tmp_path / "black.png"), np.zeros((10, 20, 3), dtype="uint8"))
    cv2.imwrite(str(tmp_path / "image.png"), line_image())
    state = new_state()
    registry.run_command(state, "roi 0 2 20 5")
    registry.run_command(state, f"source file {(tmp_path / 'black.png').as_posix()}")
    registry.run_command(state, "dark 1")
    registry.run_command(state, f"source file {(tmp_path / 'image.png').as_posix()}")
    registry.run_command(state, "reference 1")
    registry.run_command(state, "mode transmission")
    return state
