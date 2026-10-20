"""Adrians kommandofiler mot hans facit, genom det riktiga programmet: samma som kor -W och jamfor i verktyg.ps1."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
MAPP = ROT / "tests" / "kommandon"
FALL = sorted(p.stem.removeprefix("testa_") for p in MAPP.glob("testa_*.txt") if (MAPP / f"facit_{p.stem[6:]}.txt").exists())


def lika(text):
    """Som lika i verktyg.ps1: mätmappens namn och residualer nära 0 får skilja; radslut och blanktecken sist ignoreras."""
    rader = []
    for rad in text.replace("\r\n", "\n").splitlines():
        rad = re.sub(r"data/(\d{8}|ÅÅÅÅMMDD)-(\d{6}|HHMMSS)(-\d+)?", "data/MAPP", rad)
        rad = re.sub(r"residual: -?[0-9.]+e-1\d", "residual: 0", rad)
        rader.append(rad.rstrip())
    while rader and not rader[-1]:
        rader.pop()
    return rader


@pytest.mark.parametrize("fall", FALL)
def test_facit(fall, tmp_path):
    """Kommandofilen matas till python -W error -m spectrometer.main i en kopia av tests/, så att data/ hamnar i tmp."""
    shutil.copytree(ROT / "tests", tmp_path / "tests")
    miljo = {**os.environ, "PYTHONPATH": str(ROT), "PYTHONUTF8": "1", "MPLBACKEND": "Agg"}
    korning = subprocess.run(
        [sys.executable, "-W", "error", "-m", "spectrometer.main"],
        input=(MAPP / f"testa_{fall}.txt").read_bytes(),
        capture_output=True,
        cwd=tmp_path,
        env=miljo,
        timeout=120,
    )
    assert korning.stderr.decode("utf-8") == ""
    assert lika(korning.stdout.decode("utf-8")) == lika((MAPP / f"facit_{fall}.txt").read_text(encoding="utf-8-sig"))