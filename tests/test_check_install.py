"""check_install.py: versionsjämförelsen, Tk-kontrollen, ARM-raden, kameraprovet och skriptet mot en tillfällig projektmapp."""

import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

import check_install

ROT = Path(__file__).resolve().parents[1]
NUMPY = check_install.version_av("numpy")


def kor_skriptet(mapp, krav, kodning="utf-8"):
    """Kopierar check_install.py och en requirements.txt till mapp och kör skriptet som test_facit kör programmet.

    Skriptet läser requirements.txt i sin egen mapp. Ger (slutkod, stdout-rader).
    """
    shutil.copy(ROT / "check_install.py", mapp / "check_install.py")
    (mapp / "requirements.txt").write_bytes(krav.encode(kodning))
    miljo = {**os.environ, "PYTHONUTF8": "1"}
    korning = subprocess.run([sys.executable, "check_install.py"], capture_output=True, cwd=mapp, env=miljo, timeout=120)
    return korning.returncode, korning.stdout.decode("utf-8").splitlines()


def nivaer(rader, namn):
    """Nivån (OK, VARNING, FEL) på raderna i rader vars text börjar med namn."""
    return [niva for niva, text in rader if text.startswith(namn)]


def numpy_med(steg):
    """Det installerade numpys version med talet på plats 0, 1 eller 2 ökat med ett (och talen efter nollade)."""
    tal = check_install.delar(NUMPY)[:3]
    tal[steg] += 1
    tal[steg + 1 :] = [0] * (2 - steg)
    return ".".join(str(t) for t in tal)


def test_package_not_installed_gives_fel(tmp_path):
    """TES-25: en rad med ett oinstallerat paket ger FEL-rad och slutkod 1."""
    kod, rader = kor_skriptet(tmp_path, "ingen-sadan-modul==1.0\n")
    assert kod == 1
    assert any(rad.startswith("FEL  ingen-sadan-modul är inte installerat") for rad in rader)
    assert rader[-1].startswith("Installationen stämmer inte:")


def test_utf8_with_bom_is_accepted(tmp_path):
    """En requirements.txt med BOM (PowerShell 5 skriver dem) läses som vanligt."""
    _, rader = kor_skriptet(tmp_path, f"numpy=={NUMPY}\n", "utf-8-sig")
    assert f"OK  numpy {NUMPY}" in rader


def test_utf16_gives_fel_row(tmp_path):
    """En requirements.txt sparad som UTF-16 ger en FEL-rad som säger vad som är fel."""
    _, rader = kor_skriptet(tmp_path, f"numpy=={NUMPY}\n", "utf-16")
    assert any(rad.startswith("FEL  requirements.txt är inte sparad som UTF-8") for rad in rader)


@pytest.mark.parametrize(
    ("krav", "installerad", "niva"),
    [
        ("2.5.4", "2.5.4", "OK"),
        ("2.5.4", "2.5.3", "VARNING"),
        ("5.0.0.93", "5.0.0.94", "VARNING"),
        ("2.5.4", "2.6.4", "FEL"),
        ("2.5.4", "3.5.4", "FEL"),
        ("2.5", "2.5.0", "OK"),
    ],
)
def test_version_levels(krav, installerad, niva):
    """INS-03: patchnivån ger VARNING, minor och major ger FEL."""
    assert check_install.jamfor(krav, installerad) == niva


def test_patch_difference_is_varning_and_minor_is_fel(tmp_path):
    """INS-03 mot en riktig requirements.txt: numpy med annan patch ger VARNING (slutkod 0), annan minor ger FEL."""
    (tmp_path / "requirements.txt").write_text(f"numpy=={numpy_med(2)}\n", encoding="utf-8")
    rader = check_install.kolla_bibliotek(tmp_path)
    assert nivaer(rader, "numpy") == ["VARNING"]
    assert check_install.visa(rader) == 0
    (tmp_path / "requirements.txt").write_text(f"numpy=={numpy_med(1)}\n", encoding="utf-8")
    assert nivaer(check_install.kolla_bibliotek(tmp_path), "numpy") == ["FEL"]


def test_exit_code_follows_fel_not_varning(monkeypatch, capsys):
    """Slutkod 0 med bara VARNING och INFO, slutkod 1 med ett FEL; slutraden följer."""
    monkeypatch.setattr(check_install, "kor_alla", lambda rot: [("VARNING", "a"), ("INFO", "b")])
    assert check_install.main([]) == 0
    assert capsys.readouterr().out.splitlines() == ["VARNING  a", "INFO  b", "Installationen stämmer."]
    monkeypatch.setattr(check_install, "kor_alla", lambda rot: [("OK", "a"), ("FEL", "b")])
    assert check_install.main([]) == 1
    assert capsys.readouterr().out.splitlines()[-1].startswith("Installationen stämmer inte: 1 fel.")


@pytest.mark.parametrize("namn", ["opencv-python", "opencv-python-headless"])
def test_either_opencv_package_is_accepted(tmp_path, namn):
    """INS-16: requirements.txt får säga opencv-python eller opencv-python-headless; vilket som är installerat duger."""
    hittat, version = check_install.installerad("opencv-python")
    assert version is not None
    (tmp_path / "requirements.txt").write_text(f"{namn}=={version}\n", encoding="utf-8")
    assert nivaer(check_install.kolla_bibliotek(tmp_path), hittat) == ["OK"]


def fake_tkinter(monkeypatch, fel):
    """Sätter in en låtsas-tkinter vars Tk() kastar TclError(fel), eller lyckas om fel är None."""
    tk = types.ModuleType("tkinter")
    tk.TclError = type("TclError", (Exception,), {})

    class Fonster:
        def destroy(self):
            pass

    def Tk():
        if fel is not None:
            raise tk.TclError(fel)
        return Fonster()

    tk.Tk = Tk
    monkeypatch.setitem(sys.modules, "tkinter", tk)


def test_tk_ok(monkeypatch):
    """INS-07: Tk som öppnar ett fönster är OK."""
    fake_tkinter(monkeypatch, None)
    assert [niva for niva, _ in check_install.kolla_tk()] == ["OK"]


def test_tk_without_display_is_varning(monkeypatch):
    """INS-07: ingen skärm (SSH) är VARNING, inte FEL."""
    fake_tkinter(monkeypatch, "no display name and no $DISPLAY environment variable")
    assert [niva for niva, _ in check_install.kolla_tk()] == ["VARNING"]


def test_tk_broken_or_missing_is_fel_with_action(monkeypatch):
    """INS-07: en Tk som inte startar, eller ingen tkinter alls, är FEL och säger vad man gör per system."""
    fake_tkinter(monkeypatch, "Can't find a usable init.tcl")
    [(niva, text)] = check_install.kolla_tk()
    assert niva == "FEL"
    assert "sudo pacman -S tk" in text
    monkeypatch.setitem(sys.modules, "tkinter", None)  # import tkinter ger då ImportError
    [(niva, text)] = check_install.kolla_tk()
    assert niva == "FEL"
    assert "python3-tk" in text


def test_arm_emulation_info():
    """INS-05: x64-Python på en dator som säger ARM64 ger INFO; vanlig x64 och vanlig ARM64 ger ingen rad."""
    assert check_install.arm_emulering("win-amd64", "AMD64", {"PROCESSOR_ARCHITEW6432": "ARM64"})
    assert not check_install.arm_emulering("win-amd64", "AMD64", {})
    assert not check_install.arm_emulering("win-arm64", "ARM64", {"PROCESSOR_ARCHITEW6432": "ARM64"})
    assert not check_install.arm_emulering("linux-x86_64", "x86_64", {})


class FakeCamera:
    """Låtsaskamera i stället för cv2.VideoCapture: ger bilderna i listan, en per read."""

    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True


def use_fake_camera(monkeypatch, camera):
    """Byter cv2.VideoCapture mot en funktion som ger camera."""
    import cv2

    monkeypatch.setattr(cv2, "VideoCapture", lambda index, backend: camera)


def test_camera_rows_and_dark_first_image(monkeypatch):
    """--kamera: en rad per bild med storleken, och OBS när första bilden är mörk; kameran släpps."""
    camera = FakeCamera([np.full((4, 6, 3), value, np.uint8) for value in (10, 100, 100)])
    use_fake_camera(monkeypatch, camera)
    rader = check_install.kolla_kamera(0, 3)
    assert [text for _, text in rader[:3]] == [
        "bild 1: 6 x 4, medelvärde 10.0",
        "bild 2: 6 x 4, medelvärde 100.0",
        "bild 3: 6 x 4, medelvärde 100.0",
    ]
    assert rader[3][0] == "INFO"
    assert rader[3][1].startswith("OBS mörk första bild")
    assert camera.released


def test_camera_that_does_not_open_is_fel(monkeypatch):
    """--kamera N för en kamera som inte öppnas: FEL med camera.open_failed."""
    use_fake_camera(monkeypatch, FakeCamera([], opened=False))
    [(niva, text)] = check_install.kolla_kamera(2, 3)
    assert niva == "FEL"
    assert text.startswith("camera.open_failed: kunde inte öppna kamera 2.")


def test_arguments():
    """--kamera N och --bilder K; fel flagga eller icke-heltal ger ValueError."""
    assert check_install.lasa_argument([]) == (None, 3)
    assert check_install.lasa_argument(["--kamera", "0", "--bilder", "5"]) == (0, 5)
    for fel in (["--kamera"], ["--kamera", "x"], ["--bilder", "0"], ["--hej", "1"]):
        with pytest.raises(ValueError, match="--|använd"):
            check_install.lasa_argument(fel)