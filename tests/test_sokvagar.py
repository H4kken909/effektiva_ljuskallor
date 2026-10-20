"""Sökvägar (R12): bakåtsnedstreck i Windows-rader, mellanslag och åäö i mappnamn, bilder förbi cv2:s sökvägar."""

import json
import os

import cv2
import numpy as np
import pytest

from spectrometer import registry, session, source


def line_image():
    """En bild 10 x 20 med en lodrät linje i kolumn 12."""
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    return image


def write_png(path, image):
    """Skriver en png utan cv2.imwrite, så testet inte beror på det som testas."""
    cv2.imencode(".png", image)[1].tofile(path)


def read_png(path):
    """Läser en png utan cv2.imread."""
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)


def source_path(system, line):
    """Kör raden som om os.name vore system ("nt" eller "posix") och ger sökvägen som source fick."""
    state = session.new_state(session.DEFAULTS)
    with pytest.MonkeyPatch.context() as patch:  # bara runt anropet: pathlib väljer Windows eller Posix efter os.name
        patch.setattr(os, "name", system)
        registry.run_command(state, line)
    return state["settings"]["source"][1]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (r"source file C:\bilder\a.png", r"C:\bilder\a.png"),
        (r'source file "C:\bilder\a.png"', r"C:\bilder\a.png"),
        (r'source file "C:\bilder\"', "C:\\bilder\\"),
        ("source file C:/bilder/a.png", "C:/bilder/a.png"),
    ],
)
def test_windows_paths_keep_backslashes(line, expected):
    """ROB-08: på Windows (os.name nt) överlever bakåtsnedstrecken med och utan citattecken."""
    assert source_path("nt", line) == expected


def test_posix_removes_unquoted_backslashes():
    """TES-06: utan Windows-regeln tar shlex bort bakåtsnedstrecken (så C:\\bilder\\a.png blir C:bildera.png)."""
    assert source_path("posix", r"source file C:\bilder\a.png") == "C:bildera.png"
    assert source_path("posix", r'source file "C:\bilder\a.png"') == r"C:\bilder\a.png"
    assert source_path("posix", "source file C:/bilder/a.png") == "C:/bilder/a.png"


def test_space_and_aao_all_the_way(tmp_path, monkeypatch, capsys):
    """ROB-09, TES-07: source, step och save med mellanslag och åäö; bilderna går aldrig via cv2.imread eller imwrite."""

    def forbidden(*args):
        raise AssertionError("imread och imwrite klarar inte åäö i Windows-sökvägar")

    monkeypatch.setattr(cv2, "imread", forbidden)
    monkeypatch.setattr(cv2, "imwrite", forbidden)
    folder = tmp_path / "mätning 1"
    folder.mkdir()
    write_png(folder / "rå bild.png", line_image())
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f'source file "{(folder / "rå bild.png").as_posix()}"')
    registry.run_command(state, "step")
    registry.run_command(state, f'save "{(tmp_path / "ut mapp").as_posix()}"')
    capsys.readouterr()
    saved = next((tmp_path / "ut mapp").iterdir())
    assert sorted(p.name for p in saved.iterdir()) == ["README.txt", "raw.png", "settings.json", "spectrum.csv"]
    np.testing.assert_array_equal(read_png(saved / "raw.png"), line_image())
    assert json.loads((saved / "settings.json").read_text(encoding="utf-8"))["source"][1].endswith("rå bild.png")


def test_empty_file_is_not_an_image(tmp_path):
    """Felmeddelandet för en fil som inte är en bild är det gamla, också för en tom fil."""
    path = tmp_path / "tom.png"
    path.write_bytes(b"")
    with pytest.raises(RuntimeError, match="camera.open_failed: Could not open .* as image"):
        source.open_source("file", path)
