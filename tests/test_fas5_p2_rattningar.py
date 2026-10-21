"""Fas 5 paket 2: reset behåller startflaggorna, save_png med åäö, snap-gräns, trasig spectrum.csv och roi mot background."""

import cv2
import numpy as np
from test_elias import error_text, line_image, new_state
from test_extraktion import band_state
from test_flaggor import prompt_lines

from spectrometer import analys, files, main, measure, registry, session


def run_file_at_start(monkeypatch, tmp_path, flags, text):
    """Kör main med flaggorna och en kommandofil (text) med --avsluta. Ger slutkoden."""
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(AssertionError("prompten visades")))
    path = tmp_path / "rader.txt"
    path.write_text(text, encoding="utf-8")
    return main.main([*flags, "--kor", path.as_posix(), "--avsluta"])


def test_reset_keeps_the_start_flags(monkeypatch, tmp_path, capsys):
    """B3: reset går tillbaka till läget vid start, med --output och --input."""
    code = run_file_at_start(monkeypatch, tmp_path, ["--input", "bild.png", "--output", "ut"],
                             "frames 3\nreset\nshow\n")
    assert code == 0
    rows = capsys.readouterr().out.splitlines()
    assert "källa: fil bild.png" in rows
    assert "output_dir: ut" in rows
    assert "frames: 1" in rows
    assert not any("start" in row for row in rows[5:])  # nyckeln för startläget syns inte i show


def test_undo_after_reset_works_at_the_prompt(monkeypatch, capsys):
    """B3: undo efter reset lägger tillbaka läget före reset, med startflaggorna kvar."""
    prompt_lines(monkeypatch, ["frames 3", "reset", "show", "undo", "show", "quit"])
    assert main.main(["--input", "bild.png", "--output", "ut"]) == 0
    rows = capsys.readouterr().out.splitlines()
    reset_at = rows.index("Allt nollställt (som vid start).")
    undo_at = next(k for k, row in enumerate(rows) if row.startswith("Ångrat: reset"))
    for part in (rows[reset_at:undo_at], rows[undo_at:]):
        assert "källa: fil bild.png" in part
        assert "output_dir: ut" in part
    assert "frames: 1" in rows[reset_at:undo_at]
    assert "frames: 3" in rows[undo_at:]


def test_reset_works_on_a_state_without_start_settings(capsys):
    """B3: en state som inte kommer från main (som i testerna) går till standardvärdena."""
    state = new_state()
    state["settings"]["frames"] = 5
    registry.run_command(state, "reset")
    assert state["settings"] == session.DEFAULTS


def test_clear_all_keeps_the_start_settings_for_a_later_reset(monkeypatch, tmp_path, capsys):
    """B3: clear all följt av reset ger fortfarande startflaggorna."""
    run_file_at_start(monkeypatch, tmp_path, ["--output", "ut"], "set output_dir x\nclear all\nreset\nshow\n")
    assert "output_dir: ut" in capsys.readouterr().out.splitlines()


def test_save_png_with_non_ascii_path(tmp_path):
    """B5: save_png klarar åäö i sökvägen (cv2.imwrite gör det inte på Windows)."""
    folder = tmp_path / "mätning åäö"
    folder.mkdir()
    path = folder / "bild.png"
    files.save_png(path, line_image())
    back = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    np.testing.assert_array_equal(back, line_image())


def test_save_png_failure_is_files_write_failed(tmp_path):
    """B5: en mapp som saknas ger fortfarande files.write_failed."""
    try:
        files.save_png(tmp_path / "saknas" / "bild.png", line_image())
    except OSError as error:
        assert str(error).startswith("files.write_failed: bild.png kunde inte sparas")
    else:
        raise AssertionError("inget fel")


def test_snap_has_the_same_upper_limit_as_frames(monkeypatch):
    """B7: snap 1001 ger samma fel som frames 1001, innan källan öppnas."""
    monkeypatch.setattr(measure, "_with_source", lambda *args: (_ for _ in ()).throw(RuntimeError("källan öppnades")))
    state = new_state()
    expected = error_text(state, "frames 1001")
    assert expected == "input.invalid_argument: N ska vara högst 1000"
    assert error_text(state, "snap 1001") == expected


BROKEN_CSV = "x_px,value,valid\n0,1.5,true\n1,2.5\n2,3.5,true\n"


def broken_folder(tmp_path):
    """En mätmapp vars spectrum.csv har en rad med för få fält (rad 3). Ger mappen."""
    folder = tmp_path / "trasig"
    folder.mkdir()
    (folder / "spectrum.csv").write_text(BROKEN_CSV, encoding="utf-8")
    return folder


def test_load_of_a_broken_spectrum_csv_is_an_error_line(tmp_path):
    """B14: load ger input.invalid_argument med filen och radnumret, inte IndexError."""
    folder = broken_folder(tmp_path)
    assert error_text(new_state(), f"load {folder.as_posix()}") == (
        "input.invalid_argument: trasig/spectrum.csv rad 3: fel antal fält"
    )


def test_kor_with_a_broken_spectrum_csv_gives_no_traceback(monkeypatch, tmp_path, capsys):
    """B14: --kor FIL --avsluta med load på en trasig fil ger en Fel-rad och slutkod 1."""
    folder = broken_folder(tmp_path)
    code = run_file_at_start(monkeypatch, tmp_path, [], f"load {folder.as_posix()}\n")
    out = capsys.readouterr().out
    assert code == 1
    assert "Fel: input.invalid_argument: trasig/spectrum.csv rad 3: fel antal fält" in out
    assert "Traceback" not in out


def test_analys_script_with_a_broken_spectrum_csv(tmp_path, capsys):
    """B14: python -m spectrometer.analys toppar på en trasig fil: Fel-rad och slutkod 1."""
    folder = broken_folder(tmp_path)
    capsys.readouterr()
    code = analys.main(["toppar", folder.as_posix()])
    out = capsys.readouterr().out
    assert code == 1
    assert out.startswith("Fel: input.invalid_argument: ")
    assert "rad 3: fel antal fält" in out


def test_roi_checks_that_background_still_fits(tmp_path):
    """B19: roi som inte lämnar plats åt background N ger felet direkt och den gamla ROI:n står kvar."""
    state = band_state(tmp_path)
    registry.run_command(state, "step")
    registry.run_command(state, "background 3")
    old = state["settings"]["roi"]
    assert error_text(state, "roi 0 4 20 5") == (
        "input.invalid_argument: bakgrunden behöver 3 fria rader på båda sidor om roi (0, 4, 20, 5)"
    )
    assert state["settings"]["roi"] == old == (0, 4, 20, 2)
    assert error_text(state, "roi 0 4 20 3") is None
    assert state["settings"]["roi"] == (0, 4, 20, 3)
