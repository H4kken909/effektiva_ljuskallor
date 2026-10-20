"""1.0.32 Version och metadata: nycklarna i settings.json, settings_id, git som saknas, README.txt och version."""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest
from test_elias import line_image, new_state

from spectrometer import __version__, meta, registry

ROOT = Path(__file__).resolve().parents[1]


def saved_settings(tmp_path, lines=()):
    """Mörker ur en svart bild, en linjebild, raderna i lines, step och save. Ger (settings.json, mätmappen)."""
    black = tmp_path / "svart.png"
    image = tmp_path / "bild.png"
    cv2.imwrite(str(black), np.zeros((10, 20, 3), dtype="uint8"))
    cv2.imwrite(str(image), line_image())
    state = new_state()
    data = tmp_path / "data"
    for line in (f"source file {black.as_posix()}", "dark 2", f"source file {image.as_posix()}", *lines, "step",
                 f"save {data.as_posix()}"):
        registry.run_command(state, line)
    folder = next(data.iterdir())
    return json.loads((folder / "settings.json").read_text(encoding="utf-8")), folder


def test_settings_json_has_metadata_before_coefficients(tmp_path):
    """DAT-07/08/09/10/12/16: de nya nycklarna står före coefficients, och slutet av filen är som förut."""
    settings, folder = saved_settings(tmp_path)
    keys = list(settings)
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]
    assert keys.index("settings_id") < keys.index("coefficients")
    assert settings["program_version"] == __version__
    assert folder.name == datetime.fromisoformat(settings["measured_at"]).strftime("%Y%m%d-%H%M%S")
    assert settings["git_commit"] is None or isinstance(settings["git_commit"], str)
    assert set(settings["libraries"]) == {"python", "numpy", "opencv", "matplotlib"}
    assert re.fullmatch(r"[0-9a-f]{12}", settings["settings_id"])
    assert settings["profiles"] == {"dark": {"frames": 2, "mean": 0.0}, "response": None, "reference": None}


def test_profiles_reference(tmp_path):
    """DAT-12: referensens profil har antal bilder, kanal och första och sista x."""
    settings, _ = saved_settings(tmp_path, ["reference 1"])
    assert settings["profiles"]["reference"] == {"frames": 1, "channel": "gray", "x_first": 0.0, "x_last": 19.0}


def test_settings_id_follows_settings():
    """DAT-16: samma inställningar ger samma settings_id; tid och version räknas inte, kanalen gör det."""
    a = {"channel": "red", "roi": (1, 2, 3, 4), "measured_at": "2026-10-20T10:00:00+02:00", "program_version": "1"}
    b = dict(a, measured_at="2026-10-21T11:00:00+02:00", program_version="2")
    c = dict(a, channel="green")
    assert meta.settings_id(a) == meta.settings_id(b)
    assert meta.settings_id(a) != meta.settings_id(c)


def test_save_works_without_git(tmp_path, monkeypatch):
    """DAT-09: utan git (FileNotFoundError) blir git_commit och git_dirty null, och save fungerar ändå."""

    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(meta.subprocess, "run", no_git)
    settings, _ = saved_settings(tmp_path)
    assert settings["git_commit"] is None
    assert settings["git_dirty"] is None


def test_git_error_gives_none(monkeypatch):
    """DAT-09: git som svarar med fel (mappen är inget repo, som efter en ZIP-nedladdning) ger (None, None)."""

    def not_a_repo(*args):
        raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(meta, "_git", not_a_repo)
    assert meta.git_state() == (None, None)


def test_readme_in_folder(tmp_path):
    """DAT-24: README.txt i mätmappen med filerna, förbehållet och raderna om just den här mätningen."""
    _, folder = saved_settings(tmp_path, ["channel red"])
    text = (folder / "README.txt").read_text(encoding="utf-8")
    assert "Alla tal är relativa tal från kameran, inte watt." in text
    assert "  kanal: red" in text
    assert "  mörker: ja" in text
    assert "  kalibrerad: nej" in text
    assert f"  programversion: {__version__}" in text


def test_version_command(capsys):
    """UT-32: version skriver programmet, Python och biblioteken på en rad."""
    registry.run_command(new_state(), "version")
    line = capsys.readouterr().out.strip()
    assert line.startswith(f"spektro {__version__}, Python ")
    assert ", numpy " in line
    assert ", opencv " in line
    assert ", matplotlib " in line


def test_version_matches_changelog():
    """PRC-12: __version__ är lika med översta numrerade rubriken i CHANGELOG.md (hoppas över utan filen)."""
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        pytest.skip("CHANGELOG.md finns inte (sandlådan)")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        found = re.match(r"#+\s*\[?v?(\d+\.\d+\.\d+)", line)
        if found:
            assert found.group(1) == __version__, "samma version överst i CHANGELOG.md som i spectrometer/__init__.py"
            return
    pytest.fail("ingen rubrik med versionsnummer i CHANGELOG.md")
