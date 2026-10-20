"""1.2.1 note och series: metadata i settings.json, en rad per save i serie.csv, och en mättad punkt vägras."""

import json
from pathlib import Path

import cv2
import pytest
from test_elias import line_image, new_state

from spectrometer import registry
from spectrometer.analysis import series


def run(state, *lines):
    """Kör raderna i ordning."""
    for line in lines:
        registry.run_command(state, line)


def test_series_rows_and_metadata(tmp_path, capsys):
    """Två strömmar ger två rader; settings.json har series note, note och seriens namn; show visar dem."""
    path = tmp_path / "led.png"
    cv2.imwrite(str(path), line_image())
    data = (tmp_path / "data").as_posix()
    state = new_state()
    run(state, f"source file {path.as_posix()}", f"set output_dir {data}", "series start roed",
        "series note current_mA=10 voltage_V=2.8 led=röd", "note röd LED, ny", "step", "save",
        "series note current_mA=20", "step", "save", "show", "series stop")
    text = capsys.readouterr().out.splitlines()
    assert f"serie roed: rad 2 i {data}/roed/serie.csv" in text
    assert text[-4:] == [f"serie: roed ({data}/roed/serie.csv)", "series note: current_mA=20 voltage_V=2.8 led=röd",
                         "note: röd LED, ny", f"serie roed stoppad: 2 rader i {data}/roed/serie.csv"]
    rows = series.load(tmp_path / "data" / "roed" / "serie.csv")
    assert [row["current_mA"] for row in rows] == [10.0, 20.0]
    assert (rows[0]["led"], rows[0]["note"], rows[0]["peak"], rows[0]["peak_x"]) == ("röd", "röd LED, ny", 200.0, 12.0)
    assert rows[0]["area"] == 200.0  # trapets: toppen 200 vid pixel 12, noll bredvid
    settings = json.loads((Path(rows[1]["folder"]) / "settings.json").read_text(encoding="utf-8"))
    assert settings["annotations"] == {"current_mA": 20.0, "voltage_V": 2.8, "led": "röd"}
    assert (settings["note"], settings["series"]) == ("röd LED, ny", "roed")
    assert state["series"] is None and state["annotations"] == {}


def test_series_errors_and_saturation(tmp_path):
    """Fel ord ger input-fel; i en serie sparas en mättad mätning inte alls (KRV-20)."""
    path = tmp_path / "full.png"
    cv2.imwrite(str(path), line_image(value=255))
    state = new_state()
    run(state, f"source file {path.as_posix()}", f"set output_dir {(tmp_path / 'data').as_posix()}")
    for line, text in (("series stop", "ingen serie pågår"), ("series note foo=1", "foo=1 ska vara NYCKEL=VÄRDE"),
                       ("series note current_mA=x", "current_mA ska vara ett tal"), ("series start a/b", "NAMN får ha")):
        with pytest.raises(ValueError, match=text):
            registry.run_command(state, line)
    run(state, "series start s", "step")
    with pytest.raises(ValueError, match="mättad"):
        registry.run_command(state, "save")
    assert not (tmp_path / "data").exists()


def test_note_alone_and_clear(capsys):
    """note ensam visar, note TEXT sätter, note clear tar bort."""
    run(new_state(), "note", "note röd 20 mA", "note", "note clear")
    assert capsys.readouterr().out.splitlines() == ["note: (ingen)", "note: röd 20 mA", "note: röd 20 mA", "note: (ingen)"]
