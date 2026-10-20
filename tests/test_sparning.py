"""1.0.31 Säker sparning: .partial, kontroll, nya försök, ledigt utrymme, Ctrl+C mitt i save och quit som frågar."""

from types import SimpleNamespace

import cv2
from test_elias import error_text, line_image, new_state, run_prompt
from test_morkret import terminal

from spectrometer import files, registry


def measured(tmp_path):
    """State med en mätning av en linjebild, och mappen där den ska sparas. Ger (state, mappen)."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    return state, tmp_path / "data"


def test_ctrl_c_during_save_leaves_nothing(monkeypatch, capsys, tmp_path):
    """ROB-14: Ctrl+C mitt i save (i cv2.imencode) ger Avbrutet. och ingen mapp, inte heller en .partial."""
    image = tmp_path / "bild.png"
    cv2.imwrite(str(image), line_image())

    def interrupted(ext, img):
        raise KeyboardInterrupt

    monkeypatch.setattr(files.cv2, "imencode", interrupted)
    data = tmp_path / "data"
    lines = [f"source file {image.as_posix()}", "step", f"save {data.as_posix()}", "quit"]
    code, out = run_prompt(monkeypatch, capsys, lines)
    assert code == 0
    assert "spektro> Avbrutet." in out
    assert list(data.iterdir()) == []


def test_failed_write_removes_partial(monkeypatch, tmp_path):
    """ROB-12: när raw.png inte går att skriva blir det files.write_failed och ingen mapp ligger kvar."""
    state, data = measured(tmp_path)
    monkeypatch.setattr(files.cv2, "imencode", lambda ext, img: (False, None))
    assert error_text(state, f"save {data.as_posix()}").startswith("files.write_failed: raw.png kunde inte sparas")
    assert list(data.iterdir()) == []


def test_rename_tries_three_times(monkeypatch, tmp_path):
    """ROB-12: PermissionError två gånger och sedan lyckat sparar; tre gånger ger felet och ingen ny mapp."""
    state, data = measured(tmp_path)
    real = files.os.replace
    failures = [PermissionError("låst"), PermissionError("låst")]

    def replace(src, dst):
        if failures:
            raise failures.pop(0)
        real(src, dst)

    monkeypatch.setattr(files.os, "replace", replace)
    monkeypatch.setattr(files.time, "sleep", lambda seconds: None)
    registry.run_command(state, f"save {data.as_posix()}")
    assert [p.suffix for p in data.iterdir()] == [""]  # en hel mapp, ingen .partial
    failures.extend([PermissionError("låst")] * 3)
    assert error_text(state, f"save {data.as_posix()}") == "låst"
    assert len(list(data.iterdir())) == 1


def test_too_little_free_space(monkeypatch, tmp_path):
    """ROB-13: under 50 MB ledigt ger files.write_failed och ingen mapp skapas."""
    state, data = measured(tmp_path)
    monkeypatch.setattr(files.shutil, "disk_usage", lambda path: SimpleNamespace(free=12 * 1024 * 1024))
    assert error_text(state, f"save {data.as_posix()}").startswith("files.write_failed: bara 12 MB ledigt på ")
    assert not data.exists()


def test_quit_asks_in_terminal_when_unsaved(monkeypatch, tmp_path):
    """UX-06: quit i en terminal med en osparad mätning frågar; n stannar kvar, efter save frågar den inte."""
    state, data = measured(tmp_path)
    asked = terminal(monkeypatch, ["n", "j"])
    assert registry.run_command(state, "quit") is None
    assert registry.run_command(state, "quit") is True
    assert asked == ["Mätningen är inte sparad. Avsluta ändå? (j/n) "] * 2
    registry.run_command(state, f"save {data.as_posix()}")
    assert registry.run_command(state, "quit") is True
    assert len(asked) == 2
