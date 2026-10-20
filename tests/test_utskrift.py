"""Utskriftsformatet: out.fmt, residualen utan 2.27374e-13 och felkatalogen."""

import subprocess
import sys
from pathlib import Path

import numpy as np

from spectrometer import out, registry, session

ROT = Path(__file__).resolve().parents[1]


def test_fmt_same_as_g():
    for x in (200.0, 0.5, 2.27374e-13, 412, np.float64(1.5), -0.0, 123456789.0, np.mean([10.0, 10.0])):
        assert out.fmt(x) == f"{x:g}"


def test_residual_zero_not_cpu_noise(tmp_path, capsys):
    points = tmp_path / "p.csv"
    points.write_text("pixel,wavelength_nm,check\n100,500,0\n200,600,0\n", encoding="utf-8")
    registry.run_command(session.new_state(session.DEFAULTS), f"calibrate {points.as_posix()}")
    residuals = [row for row in capsys.readouterr().out.splitlines() if row.startswith("residual")]
    assert residuals == ["residual: 0", "residual: 0"]
    assert out.fmt(round(-1e-12, 6) + 0.0) == "0"  # + 0.0 gör -0 till 0


def test_felkatalog(tmp_path):
    target = tmp_path / "felkatalog.md"
    run = subprocess.run([sys.executable, str(ROT / "tools" / "felkatalog.py"), str(target)], capture_output=True)
    assert run.returncode == 0
    text = target.read_text(encoding="utf-8")
    assert "| cmd_save | ValueError | input.missing_data | Ingen mätning än. Kör step först. |" in text
    assert "| load_points | ValueError | input.invalid_argument | {name} rad {line_no}: fel rubrik," in text
    assert "| open_source | RuntimeError | camera.open_failed |" in text
