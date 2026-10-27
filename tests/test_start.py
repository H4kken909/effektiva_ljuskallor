import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from helpers import command_file

import spektro
from spectrometer import __version__, main


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as done:
        main.main(["--version"])
    assert done.value.code == 0
    assert capsys.readouterr().out == f"spektro {__version__}\n"


def test_run_exit_gives_0_or_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("the prompt was shown"))
    path = command_file(tmp_path, "frames 2\nshow\n")
    assert main.main(["--run", path, "--exit"]) == 0
    assert "frames: 2" in capsys.readouterr().out
    path = command_file(tmp_path, "frames three\n")
    assert main.main(["--run", path, "--exit"]) == 1


ROOT = Path(__file__).resolve().parents[1]


def start(tmp_path, indata):
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1", "MPLBACKEND": "Agg"}
    run_result = subprocess.run([sys.executable, "-m", "spectrometer.main"], input=indata.encode("utf-8"),
                             capture_output=True, cwd=tmp_path, env=env, timeout=120)
    return run_result.returncode, run_result.stdout.decode("utf-8").splitlines()


def test_program_starts_and_exits(tmp_path):
    code, rows = start(tmp_path, "help\nquit\n")
    assert code == 0
    assert rows[-1].endswith("Quitting.")


def test_bad_command_in_file_gives_exit_code_1(tmp_path):
    code, rows = start(tmp_path, "foo\nquit\n")
    assert code == 1
    assert any("unknown command foo" in row for row in rows)


def test_spektro_builds_venv_command(monkeypatch, tmp_path):
    commands = []

    def run(command):
        commands.append([str(d) for d in command])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    requirements = tmp_path / "requirements.txt"
    requirements.write_text("numpy\n", encoding="utf-8")
    monkeypatch.setattr(spektro, "run", run)
    monkeypatch.setattr(spektro, "REQUIREMENTS", requirements)
    monkeypatch.setattr(spektro, "VENV", tmp_path / ".venv")
    monkeypatch.setattr(spektro, "VENV_PY", tmp_path / ".venv" / "bin" / "python")
    monkeypatch.setattr(spektro, "MARKER", tmp_path / "marker")
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "other"))
    (tmp_path / ".venv").mkdir()
    spektro.MARKER.parent.mkdir(exist_ok=True)
    spektro.prepare_venv()
    assert commands[0][1:4] == ["-m", "venv", str(tmp_path / ".venv")]
    assert commands[1][1:4] == ["-m", "pip", "install"]
    assert commands[1][-2:] == ["-r", str(requirements)]
