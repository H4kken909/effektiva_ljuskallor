"""1.0.35 Hjälpkommandon: reset, undo, history, history save, clear och set."""

import sys

import cv2
from test_elias import error_text, line_image, new_state, run_prompt
from test_kedjan import ready

from spectrometer import registry, session


def typed(state, *lines):
    """Raderna som vid prompten (registry.run_line); ett fel sväljs som main gör (raden sparas med status fel)."""
    for line in lines:
        try:
            registry.run_line(state, line)
        except (ValueError, RuntimeError, OSError):
            pass


def image_file(tmp_path):
    """En linjebild (pixel 12 = 200) i tmp_path, som sökväg med snedstreck framåt."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    return path.as_posix()


def test_reset(capsys):
    """KOM-13: reset ger samma state som vid start (inte i en terminal: utan fråga)."""
    state = new_state()
    typed(state, "frames 3", "channel red")
    state["dark"] = 1.0
    capsys.readouterr()
    registry.run_command(state, "reset")
    assert capsys.readouterr().out == "Allt nollställt (som vid start).\n"
    assert state["settings"] == session.DEFAULTS
    assert state["dark"] is None


def test_reset_asks_in_a_terminal(monkeypatch, capsys):
    """UX-25: i en terminal med mörker eller kalibrering bara en fråga; reset ja nollställer. Utan data ingen fråga."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    state = new_state()
    state["dark"], state["coefficients"] = 1.0, 2.0
    registry.run_command(state, "reset")
    assert capsys.readouterr().out == "Du förlorar mörker, kalibrering. Skriv reset ja för att fortsätta.\n"
    assert state["dark"] == 1.0
    registry.run_command(state, "reset ja")
    assert state["dark"] is None
    registry.run_command(state, "reset")
    assert capsys.readouterr().out.splitlines()[-1] == "Allt nollställt (som vid start)."
    assert error_text(state, "reset nej") == "input.invalid_argument: reset tar inget ord, eller ja"


def test_undo_at_the_prompt(monkeypatch, capsys):
    """KOM-12: undo ångrar en rad i taget, senaste först; när inget finns kvar blir det ett fel."""
    lines = ["frames 3", "channel red", "undo", "show", "undo", "undo", "quit"]
    code, out = run_prompt(monkeypatch, capsys, lines)
    assert code == 1
    assert "spektro> Ångrat: channel red" in out
    assert "channel: gray\noutput_dir: data\nframes: 3" in out
    assert "spektro> Ångrat: frames 3" in out
    assert "spektro> Fel: input.missing_data: inget att ångra" in out


def test_undo_gives_back_the_old_dark(tmp_path):
    """KOM-12: undo efter ett nytt mörker ger tillbaka det gamla (samma objekt) och glömmer mätningen; step ångras inte."""
    black = tmp_path / "svart.png"
    cv2.imwrite(str(black), line_image(value=0))
    state = new_state()
    typed(state, f"source file {black.as_posix()}", "dark 1")
    first = state["dark"]
    typed(state, f"source file {image_file(tmp_path)}", "step", "dark 2", "undo")
    assert state["dark"] is first
    assert state["spectrum"] is None
    typed(state, "undo")
    assert state["settings"]["source"] == ("file", black.as_posix())


def test_undo_keeps_five_steps():
    """UNDO_STEPS: fem steg tillbaka, sedan inget mer."""
    state = new_state()
    typed(state, *(f"frames {n}" for n in range(2, 9)))
    typed(state, *(["undo"] * 5))
    assert state["settings"]["frames"] == 3
    assert error_text(state, "undo") == "input.missing_data: inget att ångra"


def test_history_and_history_save(tmp_path, capsys):
    """KOM-09, KOM-10: history visar raderna med fel och ångrade; history save sparar bara det som run ska göra om."""
    state = new_state()
    typed(state, "frames 2", "foo", "help", "channel red", "frames 3", "undo")
    capsys.readouterr()
    registry.run_line(state, "history")
    assert capsys.readouterr().out.splitlines() == [
        "  1  frames 2",
        "  2  foo  (fel)",
        "  3  help",
        "  4  channel red",
        "  5  frames 3  (ångrad)",
        "  6  undo",
    ]
    registry.run_line(state, "history 2")
    assert capsys.readouterr().out.splitlines() == ["  6  undo", "  7  history"]
    path = (tmp_path / "sparad.txt").as_posix()
    registry.run_line(state, f"history save {path}")
    assert capsys.readouterr().out == f"history: 2 rader sparade i {path}\n"
    assert (tmp_path / "sparad.txt").read_text(encoding="utf-8").splitlines()[1:] == ["frames 2", "channel red"]
    assert error_text(state, f"history save {path}") == (
        f"input.invalid_argument: {path} finns redan, history save skriver inte över"
    )
    again = new_state()
    registry.run_command(again, f"run {path}")
    assert (again["settings"]["frames"], again["settings"]["channel"]) == (2, "red")


def test_history_empty(capsys):
    """history utan rader säger det."""
    registry.run_command(new_state(), "history")
    assert capsys.readouterr().out == "history: inga rader än\n"


def test_clear_parts(tmp_path, capsys):
    """KOM-14, KOM-15: clear tar bort en del och det som mättes med den; inställningarna står kvar."""
    state, _ = ready(tmp_path)
    registry.run_command(state, "clear reference")
    assert state["reference"] is None
    assert state["response"] is not None
    registry.run_command(state, "clear response")
    assert (state["response"], state["use_response"]) == (None, False)
    state, _ = ready(tmp_path)
    capsys.readouterr()
    registry.run_command(state, "clear dark")
    assert capsys.readouterr().out.splitlines() == ["Referensen glömd. Kör reference igen.", "mörker: borttaget"]
    assert (state["dark"], state["reference"]) == (None, None)
    assert state["coefficients"] is not None
    state, _ = ready(tmp_path)
    capsys.readouterr()
    registry.run_command(state, "clear calibration")
    assert capsys.readouterr().out.splitlines() == [
        "Responsen glömd. Kör response build igen.",
        "Referensen glömd. Kör reference igen.",
        "kalibrering: borttagen, x är pixlar igen",
    ]
    assert (state["coefficients"], state["pixel_range"], state["response"]) == (None, None, None)
    state, _ = ready(tmp_path)
    registry.run_command(state, "clear all")
    assert state["settings"]["roi"] == (10, 0, 3, 2)
    assert (state["dark"], state["coefficients"], state["response"], state["reference"]) == (None, None, None, None)
    assert error_text(state, "clear allt") == (
        "input.invalid_argument: clear: välj dark, calibration, response, reference eller all"
    )


def test_set(capsys):
    """KOM-17, PRO-38: set ändrar min_response, min_reference och output_dir; tal ska vara ändliga och över 0."""
    state = new_state()
    registry.run_command(state, "set min_response 0.02")
    registry.run_command(state, "set min_reference 2")
    registry.run_command(state, "set output_dir ut")
    assert capsys.readouterr().out.splitlines() == ["min_response: 0.02", "min_reference: 2.0", "output_dir: ut"]
    assert state["settings"]["min_reference"] == 2.0
    assert error_text(state, "set min_response 0") == (
        "input.invalid_argument: min_response ska vara ett ändligt tal större än 0"
    )
    assert error_text(state, "set min_response nan").endswith("ska vara ett ändligt tal större än 0")
    assert error_text(state, "set min_response x") == "input.invalid_argument: min_response ska vara ett tal, fick x"
    assert error_text(state, "set frames 3") == (
        "input.invalid_argument: set: okänd nyckel frames, välj min_response, min_reference, output_dir"
    )
    assert error_text(state, "set min_response") == "input.invalid_argument: set: VÄRDE saknas"
