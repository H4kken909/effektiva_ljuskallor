"""1.0.38 Profiler: response save och response load, tiderna i state["taken"], åldern i show och varningen i step."""

from datetime import datetime, timedelta

import numpy as np
from test_elias import error_text
from test_metadata import saved_settings
from test_responsen import calibrated

from spectrometer import registry


def saved_response(tmp_path):
    """Kedjan till en respons (roi 10 0 3 2, red, horizontal) och response save. Ger sökvägen till respons.npz."""
    state, paths = calibrated(tmp_path)
    registry.run_command(state, f"response build {paths['kand']} 1")
    path = (tmp_path / "respons.npz").as_posix()
    registry.run_command(state, f"response save {path}")
    return path


def test_response_save_load_roundtrip(tmp_path, capsys):
    """KOM-23, KOM-24, KOM-25: samma x och values tillbaka, mätningen glöms och response on fungerar som efter build."""
    state, paths = calibrated(tmp_path)
    registry.run_command(state, f"response build {paths['kand']} 1")
    built = state["response"]
    path = (tmp_path / "respons.npz").as_posix()
    capsys.readouterr()
    registry.run_command(state, f"response save {path}")
    assert capsys.readouterr().out == f"respons: sparad i {path}\n"
    state["response"], state["spectrum"] = None, {"x": "gammal"}
    registry.run_command(state, f"response load {path}")
    assert capsys.readouterr().out == f"respons: laddad ur {path}, 3 av 3 positioner giltiga\n"
    np.testing.assert_array_equal(state["response"]["x"], built["x"])
    np.testing.assert_array_equal(state["response"]["values"], built["values"])
    assert (state["response"]["frames"], state["response"]["known_file"]) == (1, paths["kand"])
    assert state["spectrum"] is None
    assert state["taken"]["response"].isoformat(timespec="seconds") == str(np.load(path)["taken"])
    registry.run_command(state, "response on")
    registry.run_command(state, "step")
    assert capsys.readouterr().out.splitlines()[-1] == "Topp 200 vid våglängd (nm) 520 (1 bild)"
    assert error_text(state, f"response save {path}") == (
        f"input.invalid_argument: {path} finns redan, response save skriver inte över"
    )


def test_response_load_wrong_roi(tmp_path):
    """KOM-24: annan roi, kanal eller axis vägras, och den gamla responsen står kvar."""
    path = saved_response(tmp_path)
    state, _ = calibrated(tmp_path)
    registry.run_command(state, "roi 10 0 3 1")
    assert error_text(state, f"response load {path}") == (
        "input.invalid_argument: responsen gjordes för roi 10 0 3 2, nu roi 10 0 3 1"
    )
    registry.run_command(state, "roi 10 0 3 2")
    registry.run_command(state, "channel green")
    assert error_text(state, f"response load {path}") == (
        "input.invalid_argument: responsen gjordes för kanal red, nu kanal green"
    )
    assert state["response"] is None


def test_response_load_other_calibration_warns(tmp_path, capsys):
    """PRO-07: en annan kalibrering ger en varning men laddar; utan kalibrering ett fel."""
    path = saved_response(tmp_path)
    state, _ = calibrated(tmp_path)
    shifted = tmp_path / "punkter_495.csv"
    shifted.write_text("pixel,wavelength_nm,check\n10,495,0\n12,515,0\n", encoding="utf-8")
    registry.run_command(state, f"calibrate {shifted.as_posix()}")
    capsys.readouterr()
    registry.run_command(state, f"response load {path}")
    assert capsys.readouterr().out.splitlines()[0] == "Varning: kalibreringen är en annan än när responsen gjordes"
    assert state["response"] is not None
    registry.run_command(state, "clear calibration")
    assert error_text(state, f"response load {path}") == "input.missing_data: ingen kalibrering, kör calibrate först"


def test_response_load_wrong_file(tmp_path):
    """KOM-25: en textfil, en tom fil, en .npy och en .npz utan x ger samma fel; en fil som saknas ger OSError-texten."""
    state, _ = calibrated(tmp_path)
    (tmp_path / "text.npz").write_text("inte en npz", encoding="utf-8")
    (tmp_path / "tom.npz").write_bytes(b"")
    np.save(tmp_path / "en.npy", np.arange(3.0))
    np.savez(tmp_path / "utan_x.npz", values=np.arange(3.0))
    for name in ("text.npz", "tom.npz", "en.npy", "utan_x.npz"):
        assert error_text(state, f"response load {(tmp_path / name).as_posix()}") == (
            f"input.invalid_argument: {name} är ingen responsfil från response save"
        ), name
    assert error_text(state, f"response load {(tmp_path / 'saknas.npz').as_posix()}").startswith("[Errno 2]")
    assert error_text(state, "response save x.npz") == "input.missing_data: ingen respons, kör response build först"


def test_taken_and_age_in_show(tmp_path, capsys):
    """PRO-10, PRO-11: dark, calibrate, response och reference får en tid; show skriver åldern först från 10 min."""
    state, paths = calibrated(tmp_path)
    registry.run_command(state, f"response build {paths['kand']} 1")
    registry.run_command(state, "reference 1")
    assert set(state["taken"]) == {"dark", "calibrate", "response", "reference"}
    capsys.readouterr()
    registry.run_command(state, "show")
    rows = capsys.readouterr().out.splitlines()
    assert "mörker: ja" in rows
    assert "referens: ja" in rows
    now = datetime.now().astimezone()
    state["taken"] = state["taken"] | {"dark": now - timedelta(minutes=47), "reference": now - timedelta(minutes=12)}
    registry.run_command(state, "show")
    rows = capsys.readouterr().out.splitlines()
    assert "mörker: ja (för 47 min sedan)" in rows
    assert "referens: ja (för 12 min sedan)" in rows


def test_step_warns_for_an_old_dark(tmp_path, capsys):
    """PRO-12: mörker äldre än 30 min ger en varning efter toppen; 30 min ger ingen."""
    state, _ = calibrated(tmp_path)
    for minutes, expected in ((30, []), (31, ["Varning: mörkret är 31 min gammalt (gräns 30). Kör dark igen."])):
        state["taken"] = state["taken"] | {"dark": datetime.now().astimezone() - timedelta(minutes=minutes, seconds=5)}
        capsys.readouterr()
        registry.run_command(state, "step")
        assert capsys.readouterr().out.splitlines()[1:] == expected


def test_settings_json_has_taken(tmp_path):
    """PRO-10: settings.json får taken (bara det som finns) före coefficients; slutet av filen är som förut."""
    settings, _ = saved_settings(tmp_path)
    assert set(settings["taken"]) == {"dark"}
    assert datetime.fromisoformat(settings["taken"]["dark"]).tzinfo is not None
    keys = list(settings)
    assert keys.index("settings_id") < keys.index("taken") < keys.index("coefficients")
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]
