"""1.0.30 Kedjans regler: vad som glöms, varningarna i dark och source, status och regeln för mätningen."""

from test_elias import new_state
from test_profiler import saved_response
from test_responsen import calibrated, chain_files

from spectrometer import registry


def ready(tmp_path):
    """State med mörker, kalibrering, respons och referens (filerna från test_responsen). Ger (state, filerna)."""
    state, paths = calibrated(tmp_path)
    registry.run_command(state, f"response build {paths['kand']} 1")
    registry.run_command(state, "reference 1")
    return state, paths


def test_state_changes_forget_the_measurement(tmp_path):
    """LOG-23: varje kommando som ändrar state lämnar state["spectrum"] som None. Nya kommandon ska läggas till här."""
    paths = chain_files(tmp_path)
    state = new_state()
    profile = saved_response(tmp_path)
    lines = [
        f"source file {paths['svart']}", "roi 10 0 3 2", "channel red", "axis horizontal", "frames 1", "dark 1",
        f"source file {paths['lampa']}", f"calibrate {paths['punkter']}", f"response build {paths['kand']} 1",
        "response on", "response off", "reference 1", "mode transmission", "mode direct", f"response load {profile}",
        "set min_response 0.02", "set min_reference 2", "set output_dir ut", "undo", "clear reference",
        "clear response", "clear calibration", "clear dark", "clear all", "reset",
        "rows median", "background 2", "background off", "rigg off",
    ]
    for line in lines:
        state["spectrum"] = {"x": "gammal"}  # en gammal mätning som ska glömmas
        registry.run_line(state, line)  # som vid prompten: undo har något att ångra
        assert state["spectrum"] is None, line


def test_roi_channel_axis_forget_reference(tmp_path, capsys):
    """PRO-13: axis, roi och channel glömmer referensen och responsen; efter en ny reference fungerar transmission."""
    for line in ("axis horizontal", "roi 10 0 3 2", "channel red"):
        state, _ = ready(tmp_path)
        capsys.readouterr()
        registry.run_command(state, line)
        assert state["reference"] is None, line
        assert state["response"] is None, line
        assert "Referensen glömd. Kör reference igen." in capsys.readouterr().out
    registry.run_command(state, "reference 1")
    registry.run_command(state, "mode transmission")
    capsys.readouterr()
    registry.run_command(state, "step")
    assert capsys.readouterr().out == "Topp 1 vid våglängd (nm) 500 (1 bild)\n"


def test_axis_forgets_calibration(tmp_path, capsys):
    """PRO-14 och LOG-22: axis glömmer respons, referens och kalibrering, i den ordningen."""
    state, _ = ready(tmp_path)
    capsys.readouterr()
    registry.run_command(state, "axis vertical")
    assert capsys.readouterr().out.splitlines() == [
        "Responsen glömd. Kör response build igen.",
        "Referensen glömd. Kör reference igen.",
        "Kalibreringen glömd. Kör calibrate igen.",
        "axis: vertical",
    ]
    assert state["coefficients"] is None
    assert state["pixel_range"] is None
    assert state["use_response"] is False


def test_new_calibration_forgets_response(tmp_path, capsys):
    """LOG-21: nya koefficienter glömmer responsen; samma punktfil igen ger samma koefficienter och glömmer inget."""
    state, paths = ready(tmp_path)
    registry.run_command(state, f"calibrate {paths['punkter']}")
    assert state["response"] is not None
    shifted = tmp_path / "punkter_495.csv"
    shifted.write_text("pixel,wavelength_nm,check\n10,495,0\n12,515,0\n", encoding="utf-8")
    capsys.readouterr()
    registry.run_command(state, f"calibrate {shifted.as_posix()}")
    assert state["response"] is None
    assert capsys.readouterr().out.splitlines()[-1] == "Responsen glömd. Kör response build igen."


def test_dark_and_source_warn(tmp_path, capsys):
    """PRO-15 och PRO-16: dark varnar när en respons finns; byte till kamera varnar, fil mot fil gör det inte."""
    state, paths = ready(tmp_path)
    capsys.readouterr()
    registry.run_command(state, f"source file {paths['svart']}")
    assert "källan ändrad" not in capsys.readouterr().out
    registry.run_command(state, "dark 1")
    assert "Varning: responsen byggdes med det gamla mörkret" in capsys.readouterr().out
    registry.run_command(state, "source camera 0")
    assert capsys.readouterr().out.splitlines() == [
        "source camera 0",
        "Varning: källan ändrad, mörker och referens kan vara fel",
    ]


def test_status_follows_the_chain(tmp_path, capsys):
    """KOM-43: status visar kedjan och nästa steg i ordningen dark, calibrate, response build, reference, step."""
    paths = chain_files(tmp_path)
    state = new_state()
    rounds = [
        [],
        [f"source file {paths['svart']}", "dark 1", f"source file {paths['lampa']}", "roi 10 0 3 2", "channel red"],
        [f"calibrate {paths['punkter']}"],
        [f"response build {paths['kand']} 1"],
        ["reference 1"],
    ]
    seen = []
    for lines in rounds:
        for line in lines:
            registry.run_command(state, line)
        capsys.readouterr()
        registry.run_command(state, "status")
        seen.append(capsys.readouterr().out.splitlines()[-1])
    assert seen == [
        "Nästa: dark (blockera ljusvägen)",
        "Nästa: calibrate FIL",
        "Nästa: response build FIL",
        "Nästa: reference (utan prov)",
        "Nästa: step",
    ]
    registry.run_command(state, "status")
    assert capsys.readouterr().out.splitlines()[0] == "mörker ja  kalibrering ja  respons ja  referens ja  läge direct"
