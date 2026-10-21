"""Färgen i terminalen: pipad utskrift är exakt som förut, i en terminal kommer rich (1.1.0)."""

import io

import cv2
import numpy as np
import pytest

from spectrometer import out, registry, session


def rich_terminal(monkeypatch):
    """Låtsas att programmet körs i en terminal: rich skriver till en StringIO med färgkoder."""
    console = pytest.importorskip("rich.console")
    table = pytest.importorskip("rich.table")
    text = pytest.importorskip("rich.text")
    buffer = io.StringIO()
    monkeypatch.setattr(out, "FARG", True)
    monkeypatch.setattr(out, "_konsol", console.Console(file=buffer, force_terminal=True, width=200), raising=False)
    monkeypatch.setattr(out, "Table", table.Table, raising=False)
    monkeypatch.setattr(out, "Text", text.Text, raising=False)
    monkeypatch.setattr(out, "Live", pytest.importorskip("rich.live").Live, raising=False)
    monkeypatch.setattr(out, "track", pytest.importorskip("rich.progress").track, raising=False)
    monkeypatch.setattr(out, "_live", None)
    return buffer


def test_utan_terminal_exakt_text(capsys):
    out.say("Sparad i data/x", "ok")
    out.error("input.missing_data: Ingen mätning än. Kör step först.")
    out.warn("mättad (255 i råbilden). Sänk exponeringen.")
    out.table([("help", "Visa kommandona"), ("quit", "Avsluta")], " ")
    assert capsys.readouterr().out == (
        "Sparad i data/x\n"
        "Fel: input.missing_data: Ingen mätning än. Kör step först.\n"
        "Varning: mättad (255 i råbilden). Sänk exponeringen.\n"
        "help Visa kommandona\n"
        "quit Avsluta\n"
    )


def test_i_terminal_farg(monkeypatch):
    buffer = rich_terminal(monkeypatch)
    out.error("x")
    out.warn("y")
    text = buffer.getvalue()
    assert "\x1b[" in text
    assert "Fel: x" in text
    assert "Varning: y" in text


def test_help_som_tabell_i_terminal(monkeypatch):
    buffer = rich_terminal(monkeypatch)
    registry.run_command(session.new_state(session.DEFAULTS), "help alla")
    rows = [line for line in buffer.getvalue().splitlines() if line.strip()]
    assert len(rows) == len(registry.COMMANDS)
    assert "Visa grupperna" in rows[0]


def test_hakparenteser_star_kvar_i_terminal(monkeypatch):
    buffer = rich_terminal(monkeypatch)
    registry.run_command(session.new_state(session.DEFAULTS), "help alla")
    assert any("reset" in row and "[ja]: nollställ" in row for row in buffer.getvalue().splitlines())
    out.table([("x", "[bold]text[/bold]")], " ")
    assert "[bold]text[/bold]" in buffer.getvalue()


def test_statusrad_texten():
    state = session.new_state(session.DEFAULTS)
    assert session.status_text(state) == (
        "idle · kamera 0 · roi hela bilden · gray · direct · kalibrering nej · mörker nej · respons nej"
    )
    state["settings"]["roi"] = (0, 2, 20, 4)
    state["use_response"] = True
    state["response"] = {"x": None, "values": None}
    assert "roi 0 2 20 4" in session.status_text(state)
    assert session.status_text(state).endswith("respons på")


def test_statusrad_forlopp_och_liverad_tysta_pipat(capsys):
    out.status("idle · kamera 0")
    out.live_line("running · Topp 200 vid pixel 12")
    assert list(out.progress(range(3), "mörker")) == [0, 1, 2]
    assert capsys.readouterr().out == ""


def test_statusrad_i_terminal_bara_vid_andring(monkeypatch):
    buffer = rich_terminal(monkeypatch)
    monkeypatch.setattr(out, "_status", None)
    out.status("idle · a")
    out.status("idle · a")
    out.status("idle · b")
    assert buffer.getvalue().count("idle") == 2


def test_liverad_stangs_av_nasta_rad(monkeypatch, capsys):
    buffer = rich_terminal(monkeypatch)
    out.live_line("running · Topp 200 vid pixel 12")
    assert out._live is not None
    out.say("live stoppad")
    assert out._live is None
    assert "Topp 200" in buffer.getvalue()
    assert capsys.readouterr().out == "live stoppad\n"


def test_dark_med_forloppsrad_i_terminal(monkeypatch, tmp_path):
    buffer = rich_terminal(monkeypatch)
    path = tmp_path / "svart.png"
    cv2.imwrite(str(path), np.full((4, 6, 3), 2, dtype="uint8"))
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "dark 3")
    assert state["dark"].shape == (4, 6, 3)
    assert "mörker" in buffer.getvalue()
