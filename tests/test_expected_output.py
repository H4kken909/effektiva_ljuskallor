import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from spectrometer.core import registry, session

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "tests" / "command_files"
CASES = sorted(p.stem.removeprefix("input_") for p in FOLDER.glob("input_*.txt") if (FOLDER / f"expected_{p.stem[6:]}.txt").exists())


def normalise(text):
    rows = []
    for row in text.replace("\r\n", "\n").splitlines():
        row = re.sub(r"data/(\d{8}|YYYYMMDD)-(\d{6}|HHMMSS)(-\d+)?", "data/FOLDER", row)
        row = re.sub(r"residual: -?[0-9.]+e-1\d", "residual: 0", row)
        rows.append(row.rstrip())
    while rows and not rows[-1]:
        rows.pop()
    return rows


@pytest.mark.parametrize("case", CASES)
def test_expected_output(case, tmp_path):
    shutil.copytree(ROOT / "tests", tmp_path / "tests")
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1", "MPLBACKEND": "Agg"}
    run_result = subprocess.run(
        [sys.executable, "-W", "error", "-m", "spectrometer.main"],
        input=(FOLDER / f"input_{case}.txt").read_bytes(),
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=120,
    )
    assert run_result.stderr.decode("utf-8") == ""
    assert normalise(run_result.stdout.decode("utf-8")) == normalise((FOLDER / f"expected_{case}.txt").read_text(encoding="utf-8-sig"))


DEMO = ROOT / "examples" / "demo"


def rows(name):
    return [row for row in (DEMO / name).read_text(encoding="utf-8").splitlines() if row.strip()]


def test_every_line_in_demo_files_is_a_command():
    files = sorted(DEMO.glob("*.txt"))
    assert files
    for file_name in files:
        for row in rows(file_name.name):
            assert row.split()[0] in registry.COMMANDS, f"{file_name.name}: {row}"


def test_fallback_chain_runs_on_saved_images(monkeypatch, tmp_path, capsys):
    images = tmp_path / "examples" / "demo" / "images"
    images.mkdir(parents=True)
    light_rows = np.full((10, 20, 3), 2, dtype="uint8")
    light_rows[:, [3, 8, 14]] = 200
    lamp = np.tile(np.linspace(60, 160, 20).astype("uint8")[None, :, None], (10, 1, 3))
    image_list = {"dark": np.full((10, 20, 3), 2, dtype="uint8"), "fluorescent": light_rows, "known_lamp": lamp,
                 "reference": np.full((10, 20, 3), 120, dtype="uint8"), "sample": np.full((10, 20, 3), 60, dtype="uint8")}
    for name, image in image_list.items():
        cv2.imwrite(str(images / f"{name}.png"), image)
    (tmp_path / "examples" / "demo" / "points.csv").write_text(
        "pixel,wavelength_nm,check\n0,400,0\n10,500,0\n5,450,1\n", encoding="utf-8")
    (tmp_path / "examples" / "demo" / "known.csv").write_text(
        "wavelength_nm,relative_power_per_nm\n390,1\n500,2\n600,1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = str(tmp_path / "data")
    for row in rows("fallback.txt"):
        registry.run_command(state, row)
    out = capsys.readouterr().out
    assert "dark: 1 frame" in out
    assert "response: 20 of 20 positions valid" in out
    assert state["mode"] == "transmission"
    assert len(list((tmp_path / "data").iterdir())) == 1


TOP = "Peak 200 at pixel 12 (1 frame)"


def test_quickstart_gives_the_peak(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(ROOT)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = str(tmp_path)
    for line in ("source file tests/data/images/rand_x12.png", "step", "save"):
        registry.run_command(state, line)
    rows = capsys.readouterr().out.splitlines()
    assert "source file tests/data/images/rand_x12.png" in rows
    assert TOP in rows
    assert any(row.startswith("Saved in ") for row in rows)
    assert len(list(tmp_path.iterdir())) == 1


def test_readme_promises_the_same_line():
    assert TOP in (ROOT / "README.md").read_text(encoding="utf-8")
