"""Fas 5 P1: step utan giltig position, calibrate save (avrundning, mättnad), settings.json-kalibrering, settings_id."""

import json

import cv2
import numpy as np
from test_elias import error_text, line_image, new_state
from test_kedjan import ready
from test_noggrannhet import calibrated_on_a_line, image, lines

from spectrometer import registry


def test_calibrate_save_rounds_nm_per_pixel_and_resolution(tmp_path, capsys):
    """F01: en ulp-störning i koefficienterna ger ändå exakt 10 och 20 i JSON-filen (samma på alla datorer)."""
    state, _ = calibrated_on_a_line(tmp_path)
    state["coefficients"] = np.array([400.00000000000045, 9.999999999999966])
    registry.run_command(state, "step")
    path = tmp_path / "kalibrering.json"
    registry.run_command(state, f"calibrate save {path.as_posix()}")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["nm_per_pixel"] == 10.0
    assert saved["resolution_nm"] == 20.0


def test_calibrate_save_saturated_line_has_no_resolution(tmp_path, capsys):
    """T58: en mättad linje ger resolution_nm null och en varning, inte en bredd av den avklippta toppen."""
    state, _ = calibrated_on_a_line(tmp_path)
    flat = tmp_path / "mattad.png"
    cv2.imwrite(str(flat), image({10: 100, 11: 255, 12: 255, 13: 255, 14: 100}))
    registry.run_command(state, f"source file {flat.as_posix()}")
    registry.run_command(state, "step")
    assert state["spectrum"]["saturated"].any()
    path = tmp_path / "mattad.json"
    rows = lines(capsys, state, f"calibrate save {path.as_posix()}")
    assert json.loads(path.read_text(encoding="utf-8"))["resolution_nm"] is None
    assert "Varning: upplösning okänd, högsta toppen är mättad" in rows
    assert not any(row.startswith("upplösning:") for row in rows)


def test_step_without_valid_position_refuses_and_forgets(tmp_path):
    """F06: step utan någon giltig position ger ett Fel-rad, och mätningen ligger inte kvar för save."""
    state, _ = calibrated_on_a_line(tmp_path)
    assert state["spectrum"] is not None
    state["pixel_range"] = (100.0, 200.0)  # hela ROI:n utanför kalibreringen
    assert error_text(state, "step") == (
        "input.missing_data: ingen giltig position i spektrumet (alla under tröskeln eller utanför kalibreringen)"
    )
    assert state["spectrum"] is None
    assert error_text(state, f"save {(tmp_path / 'ut').as_posix()}") == "input.missing_data: Ingen mätning än. Kör step först."
    assert not (tmp_path / "ut").exists()


def test_load_settings_forgets_response_like_points_file(tmp_path, capsys):
    """F08: calibrate MAPP/settings.json med andra koefficienter glömmer responsen; samma koefficienter behåller den."""
    state, _ = ready(tmp_path)
    assert state["response"] is not None
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"coefficients": list(state["coefficients"]), "pixel_range": [0, 19]}), encoding="utf-8")
    registry.run_command(state, f"calibrate {settings.as_posix()}")
    assert state["response"] is not None
    settings.write_text(json.dumps({"coefficients": [395, 10], "pixel_range": [0, 19]}), encoding="utf-8")
    capsys.readouterr()
    registry.run_command(state, f"calibrate {settings.as_posix()}")
    assert state["response"] is None and state["use_response"] is False
    assert capsys.readouterr().out.splitlines()[-1] == "Responsen glömd. Kör response build igen."


def test_reference_warns_when_all_positions_are_under_min_reference(tmp_path, capsys):
    """F06: reference på en bild där ingen position når min_reference varnar att referensen är oanvändbar."""
    black = tmp_path / "svart.png"
    cv2.imwrite(str(black), np.zeros((10, 20, 3), dtype="uint8"))
    state = new_state()
    for line in (f"source file {black.as_posix()}", "dark 1"):
        registry.run_command(state, line)
    rows = lines(capsys, state, "reference 1")
    assert rows[0].endswith("20 av 20 under min_reference")
    assert "Varning: alla positioner under min_reference, referensen är oanvändbar" in rows


def saved_id(tmp_path, name, lines_before=(), lines_after=()):
    """Mörker, linjebild, raderna, step, raderna efter step och save; ger settings_id och hela settings.json."""
    picture = tmp_path / "bild.png"  # samma källa i alla, annars skiljer source
    cv2.imwrite(str(picture), line_image())
    state = new_state()
    data = tmp_path / name
    for line in (f"source file {picture.as_posix()}", *lines_before, "step", *lines_after, f"save {data.as_posix()}"):
        registry.run_command(state, line)
    settings = json.loads((next(data.iterdir()) / "settings.json").read_text(encoding="utf-8"))
    return settings["settings_id"], settings


def write_rigg(tmp_path, **fields):
    """Skriver rigg.json (samma sökväg varje gång, bara fälten skiljer) och ger sökvägen."""
    path = tmp_path / "rigg.json"
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path.as_posix()


def test_settings_id_counts_rigg_controls_but_not_note(tmp_path):
    """F16: id räknas sist: olika rigg och reglage ger olika id, samma inställningar samma id, note räknas inte."""
    first, _ = saved_id(tmp_path, "a")
    again, _ = saved_id(tmp_path, "b")
    assert first == again
    with_note, settings = saved_id(tmp_path, "c", lines_after=("note hej",))
    assert settings["note"] == "hej" and with_note == first
    one, settings = saved_id(tmp_path, "d", lines_before=(f"rigg {write_rigg(tmp_path, led='A')}",))
    two, _ = saved_id(tmp_path, "e", lines_before=(f"rigg {write_rigg(tmp_path, led='B')}",))
    assert settings["rigg"] is not None
    assert len({first, one, two}) == 3
    exposed, settings = saved_id(tmp_path, "f", lines_before=("exposure -6",))
    assert settings["controls"] is not None and exposed != first
    keys = list(settings)
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]
    assert keys.index("settings_id") < keys.index("coefficients")

