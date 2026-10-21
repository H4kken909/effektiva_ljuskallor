"""Fas 5 paket 4 (BESLUT 15): mode direct när referensen glöms, clear all tar bara kedjan, image och response export."""

import cv2
import numpy as np
import pytest
from test_elias import error_text, line_image, new_state

from spectrometer import registry


def transmission_state(tmp_path):
    """En state med bildfil som källa, ett mörker (svart bild), en referens och mode transmission."""
    cv2.imwrite(str(tmp_path / "svart.png"), np.zeros((10, 20, 3), dtype="uint8"))
    cv2.imwrite(str(tmp_path / "bild.png"), line_image())
    state = new_state()
    registry.run_command(state, "roi 0 2 20 5")  # plats för background 1 på båda sidor
    registry.run_command(state, f"source file {(tmp_path / 'svart.png').as_posix()}")
    registry.run_command(state, "dark 1")
    registry.run_command(state, f"source file {(tmp_path / 'bild.png').as_posix()}")
    registry.run_command(state, "reference 1")
    registry.run_command(state, "mode transmission")
    return state


@pytest.mark.parametrize("line, said", [
    ("roi 0 0 20 5", "Referensen glömd. Kör reference igen."),
    ("channel green", "Referensen glömd. Kör reference igen."),
    ("axis vertical", "Referensen glömd. Kör reference igen."),
    ("rows median", "Referensen glömd. Kör reference igen."),
    ("background 1", "Referensen glömd. Kör reference igen."),
    ("dark 1", "referensen togs bort: kör reference igen"),
    ("clear reference", "referens: borttagen"),
    ("clear dark", "Referensen glömd. Kör reference igen."),
])
def test_losing_the_reference_leaves_transmission(tmp_path, capsys, line, said):
    """B15: när referensen glöms i mode transmission blir mode direct, det skrivs, och nästa step går."""
    state = transmission_state(tmp_path)
    capsys.readouterr()
    registry.run_command(state, line)
    rows = capsys.readouterr().out.splitlines()
    assert rows.index("mode: direct (ingen referens)") == rows.index(said) + 1
    assert (state["reference"], state["mode"]) == (None, "direct")
    assert error_text(state, "step") is None


def test_losing_the_reference_in_direct_says_nothing_about_mode(tmp_path, capsys):
    """B15: i mode direct skrivs ingen mode-rad när referensen glöms."""
    state = transmission_state(tmp_path)
    registry.run_command(state, "mode direct")
    capsys.readouterr()
    registry.run_command(state, "channel green")
    assert capsys.readouterr().out.splitlines() == ["Referensen glömd. Kör reference igen.", "channel: green"]
    assert state["mode"] == "direct"


def test_clearing_something_else_keeps_transmission(tmp_path, capsys):
    """B15: clear response med referensen kvar rör inte mode."""
    state = transmission_state(tmp_path)
    capsys.readouterr()
    registry.run_command(state, "clear response")
    assert capsys.readouterr().out.splitlines() == ["respons: borttagen"]
    assert (state["mode"], state["reference"] is not None) == ("transmission", True)


def test_help_texts_say_what_the_commands_do(capsys):
    """D3, D6, B21: roi show sparar i output_dir, start nämner tangenterna, theme har en syntaxrad och visar valet."""
    state = new_state()
    registry.run_command(state, "help")
    text = capsys.readouterr().out
    assert "roi show spara senaste bilden med ROI-rutan som roi-ÅÅÅÅMMDD-HHMMSS.png i output_dir" in text
    assert "s spara, p paus, f frys, c rensa, y skala, n normera, h hjälp" in text
    assert "theme light|dark: fönstrets färger (theme ensam visar valet)" in text
    registry.run_command(state, "help theme")
    assert "theme light eller theme dark" in capsys.readouterr().out


def test_clear_all_takes_only_the_chain(tmp_path, capsys):
    """B6 (BESLUT 9): clear all tar mörker, kalibrering, respons, referens och mode; allt annat står kvar som help säger."""
    state = transmission_state(tmp_path)
    for line in ("rows median", "background 1", "note hej", "exposure -6", "theme dark", "view normalize on"):
        registry.run_command(state, line)
    capsys.readouterr()
    registry.run_command(state, "clear all")
    assert capsys.readouterr().out.splitlines() == [
        "Mörker, kalibrering, respons och referens borttagna. Inställningarna står kvar.",
        "mode: direct (ingen referens)",
    ]
    assert (state["dark"], state["coefficients"], state["response"], state["reference"]) == (None, None, None, None)
    assert (state["use_response"], state["spectrum"], state["mode"]) == (False, None, "direct")
    assert state["settings"]["roi"] == (0, 2, 20, 5)
    assert (state["rows"], state["background"], state["note"]) == ("median", 1, "hej")
    assert state["controls"]["exposure"] == -6
    assert (state["view"]["theme"], state["view"]["normalize"]) == ("dark", True)
    assert state["image"] is not None


def test_response_export_never_overwrites(tmp_path, capsys):
    """B12 (BESLUT 10): response export vägrar om filen finns, som de andra sparkommandona."""
    from test_responsen import calibrated

    state, _ = calibrated(tmp_path)
    known = tmp_path / "kand.csv"
    known.write_text("wavelength_nm,relative_power_per_nm\n500,1\n510,1\n520,2\n", encoding="utf-8")
    registry.run_command(state, f"response build {known.as_posix()} 1")
    target = tmp_path / "respons.csv"
    registry.run_command(state, f"response export {target.as_posix()}")
    first = target.read_text(encoding="utf-8")
    text = error_text(state, f"response export {target.as_posix()}")
    assert text == f"input.invalid_argument: {target.as_posix()} finns redan, response export skriver inte över"
    assert target.read_text(encoding="utf-8") == first


def test_image_without_file_goes_to_output_dir_with_a_stamp(tmp_path, monkeypatch, capsys):
    """B17 (BESLUT 10): image utan FIL sparar bild-ÅÅÅÅMMDD-HHMMSS.png i output_dir och skriver aldrig över."""
    monkeypatch.chdir(tmp_path)
    cv2.imwrite("bild_in.png", line_image())
    state = new_state()
    registry.run_command(state, "source file bild_in.png")
    registry.run_command(state, "roi 10 0 5 10")
    registry.run_command(state, "image")
    registry.run_command(state, "image")
    saved = sorted((tmp_path / "data").glob("bild-*.png"))
    assert len(saved) == 2 and saved[1].stem.endswith("-2")
    assert capsys.readouterr().out.count("Sparad: data/bild-") == 2
    framed = cv2.imread(str(saved[0]))
    assert tuple(framed[0, 10]) == (0, 255, 0)
    assert not (tmp_path / "bild.png").exists()


def test_image_with_file_refuses_to_overwrite(tmp_path, monkeypatch):
    """B17 (BESLUT 10): image FIL vägrar om filen finns; den gamla filen rörs inte."""
    monkeypatch.chdir(tmp_path)
    cv2.imwrite("bild_in.png", line_image())
    state = new_state()
    registry.run_command(state, "source file bild_in.png")
    registry.run_command(state, "image ram.png")
    before = (tmp_path / "ram.png").read_bytes()
    assert error_text(state, "image ram.png") == "input.invalid_argument: ram.png finns redan, image skriver inte över"
    assert (tmp_path / "ram.png").read_bytes() == before
