"""Utskriftsformatet: out.fmt, residualen utan 2.27374e-13 och felkatalogen."""

import importlib.util
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


def load_felkatalog():
    """Laddar tools/felkatalog.py med sökväg (tools är inget paket)."""
    spec = importlib.util.spec_from_file_location("felkatalog", ROT / "tools" / "felkatalog.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_felkatalog_keeps_every_text_of_a_variable(tmp_path):
    """H3 a: en variabel som får olika text i flera grenar ger en rad per text, inte bara den sista."""
    source = tmp_path / "grenar.py"
    source.write_text(
        "def open_it(kind):\n"
        "    if kind:\n"
        "        message = 'camera.open_failed: första'\n"
        "    else:\n"
        "        message = 'camera.read_failed: andra'\n"
        "    raise RuntimeError(message)\n",
        encoding="utf-8")
    assert load_felkatalog().raises(source) == [
        ("open_it", "RuntimeError", "camera.open_failed", "första"),
        ("open_it", "RuntimeError", "camera.read_failed", "andra"),
    ]


def test_felkatalog_keeps_format_specs(tmp_path):
    """H3 b: formatspecifikationen i en f-sträng står kvar i texten ({x:.2f}, {n:{w}}, {s!r})."""
    source = tmp_path / "format.py"
    source.write_text(
        "def check(x, n, w, s):\n"
        "    raise ValueError(f'input.invalid_argument: {x:.2f} och {n:{w}} och {s!r} och {x}')\n",
        encoding="utf-8")
    assert load_felkatalog().raises(source) == [
        ("check", "ValueError", "input.invalid_argument", "{x:.2f} och {n:{w}} och {s!r} och {x}"),
    ]
