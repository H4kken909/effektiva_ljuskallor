"""Demons kommandofiler: varje rad är ett riktigt kommando, och reservkedjan går igenom på påhittade bilder."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from spectrometer import registry, session, source

ROT = Path(__file__).resolve().parents[1]
FILER = sorted((ROT / "demo").glob("*.txt"))


def rader(namn):
    """Raderna i demo/NAMN utan tomma rader."""
    text = (ROT / "demo" / namn).read_text(encoding="utf-8")
    return [rad for rad in text.splitlines() if rad.strip()]


def kor(state, namn):
    """Kör varje rad i demo/NAMN; ett fel kastas vidare så att testet faller."""
    for rad in rader(namn):
        registry.run_command(state, rad)


def gradient(low, high):
    """En bild 10 x 20 vars ljusstyrka ökar från low till high åt höger."""
    row = np.linspace(low, high, 20).astype("uint8")
    return np.tile(row[None, :, None], (10, 1, 3))


def make_rig_files(folder):
    """Skapar demo/bilder/*.png, punkter.csv och kand.csv av påhittade tal i folder."""
    (folder / "demo" / "bilder").mkdir(parents=True)
    lines = np.full((10, 20, 3), 2, dtype="uint8")
    lines[:, [3, 8, 14]] = 200
    images = {
        "mork": np.full((10, 20, 3), 2, dtype="uint8"),
        "lysror": lines,
        "lampa_kand": gradient(60, 160),
        "referens": np.full((10, 20, 3), 120, dtype="uint8"),
        "prov": np.full((10, 20, 3), 60, dtype="uint8"),
    }
    for name, image in images.items():
        cv2.imwrite(str(folder / "demo" / "bilder" / f"{name}.png"), image)
    (folder / "demo" / "punkter.csv").write_text("pixel,wavelength_nm,check\n0,400,0\n10,500,0\n5,450,1\n", encoding="utf-8")
    (folder / "demo" / "kand.csv").write_text("wavelength_nm,relative_power_per_nm\n390,1\n500,2\n600,1\n", encoding="utf-8")


class FakeCap:
    """Låtsaskamera som alltid ger samma bild."""

    def __init__(self, image):
        self.image = image

    def isOpened(self):
        return True

    def read(self):
        return True, self.image.copy()

    def release(self):
        pass


@pytest.mark.parametrize("fil", FILER, ids=[f.name for f in FILER])
def test_every_line_is_a_command(fil):
    assert FILER, "demo/ saknar kommandofiler"
    for rad in rader(fil.name):
        assert rad.split()[0] in registry.COMMANDS, f"{fil.name}: {rad}"


def test_reserve_chain_runs_on_stored_images(monkeypatch, tmp_path, capsys):
    make_rig_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = str(tmp_path / "data")
    kor(state, "reserv.txt")
    out = capsys.readouterr().out
    assert "mörker: 1 bild" in out
    assert "respons: 20 av 20 positioner giltiga" in out
    assert "mode: transmission" in out
    assert out.count("Topp ") == 3
    assert len(list((tmp_path / "data").iterdir())) == 1
    assert state["mode"] == "transmission"


def test_three_parts_run_with_a_camera(monkeypatch, tmp_path, capsys):
    make_rig_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(source.cv2, "VideoCapture", lambda index, backend: FakeCap(gradient(60, 160)))
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = str(tmp_path / "data")
    for namn in ("1_forbered.txt", "2_kalibrera.txt", "3_mata.txt"):
        kor(state, namn)
    out = capsys.readouterr().out
    assert "källa: kamera 0" in out
    assert "frames: 16" in out
    assert "Topp 160 vid våglängd (nm) 590" in out
    assert len(list((tmp_path / "data").iterdir())) == 1
