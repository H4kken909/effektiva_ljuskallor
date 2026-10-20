"""1.0.39 Mätdagen: rigg PATH, rigg i settings.json före coefficients, varningen i en terminal och mallen i exempel/."""

import json
import re
import sys
from pathlib import Path

from test_elias import error_text, new_state
from test_metadata import saved_settings

from spectrometer import registry

ROT = Path(__file__).resolve().parents[1]


def rig_file(tmp_path, fields):
    """Skriver rigg.json i tmp_path och ger sökvägen med snedstreck framåt."""
    path = tmp_path / "rigg.json"
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path.as_posix()


def test_rigg_reads_json(tmp_path, capsys):
    """DOK-31: rigg PATH läser objektet, varnar för tomma fält och glömmer mätningen; rigg ensam visar, off tar bort."""
    path = rig_file(tmp_path, {"slit_width_um": 100, "lamp": "lysrör", "photo": None})
    state = new_state()
    state["spectrum"] = {"x": "gammal"}
    registry.run_command(state, f"rigg {path}")
    registry.run_command(state, "rigg")
    assert capsys.readouterr().out.splitlines() == [
        f"rigg: {path} (3 fält)",
        "Varning: 1 fält är tomma: photo",
        f"rigg: {path} (3 fält)",
    ]
    assert state["rigg"] == {"file": path, "fields": {"slit_width_um": 100, "lamp": "lysrör", "photo": None}}
    assert state["spectrum"] is None
    registry.run_command(state, "rigg off")
    assert capsys.readouterr().out == "rigg: nej\n"
    assert state["rigg"] is None


def test_rigg_errors_keep_the_old(tmp_path):
    """Fel JSON, en lista i stället för ett objekt och en fil som saknas ger fel; den gamla riggen står kvar."""
    state = new_state()
    registry.run_command(state, f"rigg {rig_file(tmp_path, {'lamp': 'lysrör'})}")
    (tmp_path / "fel.json").write_text("{lamp: lysrör}", encoding="utf-8")
    (tmp_path / "lista.json").write_text("[1, 2]", encoding="utf-8")
    assert error_text(state, f"rigg {(tmp_path / 'fel.json').as_posix()}") == (
        "input.invalid_argument: fel.json är inte giltig JSON (rad 1)"
    )
    assert error_text(state, f"rigg {(tmp_path / 'lista.json').as_posix()}") == (
        "input.invalid_argument: lista.json ska vara ett JSON-objekt {...} med fälten i docs/rigg.md"
    )
    assert error_text(state, f"rigg {(tmp_path / 'saknas.json').as_posix()}").startswith("[Errno 2]")
    assert state["rigg"]["fields"] == {"lamp": "lysrör"}


def test_save_writes_rigg_before_coefficients(tmp_path):
    """DOK-31: save skriver rigg (null utan rigg) före coefficients; slutet av settings.json är som förut."""
    settings, _ = saved_settings(tmp_path)
    assert settings["rigg"] is None
    path = rig_file(tmp_path, {"grating_lines_per_mm": 1000})
    other = tmp_path / "med"  # en egen mapp: saved_settings tar första mätmappen i data/
    other.mkdir()
    settings, _ = saved_settings(other, [f"rigg {path}"])
    assert settings["rigg"] == {"file": path, "fields": {"grating_lines_per_mm": 1000}}
    keys = list(settings)
    assert keys.index("taken") < keys.index("rigg") < keys.index("coefficients")
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]


def test_save_warns_without_rigg_only_in_a_terminal(monkeypatch, tmp_path, capsys):
    """DOK-32: Varning: ingen rigg angiven, bara när stdout är en terminal (pipade facit är oförändrade)."""
    saved_settings(tmp_path)
    assert "ingen rigg" not in capsys.readouterr().out
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    (tmp_path / "tty").mkdir()
    saved_settings(tmp_path / "tty")
    assert "Varning: ingen rigg angiven (rigg rigg.json), uppställningens data saknas i settings.json" in (
        capsys.readouterr().out.splitlines()
    )


def test_template_matches_docs(capsys):
    """DOK-30: mallen exempel/rigg.json har samma fält som tabellen i docs/rigg.md, och alla är tomma."""
    template = json.loads((ROT / "exempel" / "rigg.json").read_text(encoding="utf-8"))
    documented = re.findall(r"^\| `(\w+)` \|", (ROT / "docs" / "rigg.md").read_text(encoding="utf-8"), re.MULTILINE)
    assert list(template) == documented
    registry.run_command(new_state(), f"rigg {(ROT / 'exempel' / 'rigg.json').as_posix()}")
    assert capsys.readouterr().out.splitlines()[1] == f"Varning: {len(template)} fält är tomma: {', '.join(template)}"
