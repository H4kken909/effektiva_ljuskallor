"""Snabbstarten i README ger det den lovar: Topp 200 vid pixel 12 (1 bild)."""

from pathlib import Path

from spectrometer import registry, session

ROT = Path(__file__).resolve().parents[1]
TOPP = "Topp 200 vid pixel 12 (1 bild)"


def test_quickstart_gives_the_peak(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(ROT)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = str(tmp_path)
    for line in ("source file tests/data/bilder/rand_x12.png", "step", "save"):
        registry.run_command(state, line)
    rows = capsys.readouterr().out.splitlines()
    assert "source file tests/data/bilder/rand_x12.png" in rows
    assert TOPP in rows
    assert any(row.startswith("Sparad i ") for row in rows)
    assert len(list(tmp_path.iterdir())) == 1


def test_readme_promises_the_same_line():
    readme = ROT / "README.md"
    if readme.exists():
        assert TOPP in readme.read_text(encoding="utf-8")
