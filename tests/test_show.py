"""show och ekot på vanlig svenska: källa: fil x.png, roi: hela bilden, mätning: ja; ekot skrivs som kommandot."""

import cv2
import numpy as np

from spectrometer import registry, session


def say(capsys, state, command):
    """Kör ett kommando och ger raderna det skrev."""
    registry.run_command(state, command)
    return capsys.readouterr().out.splitlines()


def test_show_default_in_plain_words(capsys):
    state = session.new_state(session.DEFAULTS)
    rows = say(capsys, state, "show")
    assert "källa: kamera 0" in rows
    assert "roi: hela bilden" in rows
    assert "mätning: nej" in rows
    assert not any("('" in row or "None" in row for row in rows)


def test_echo_is_written_as_the_command(capsys):
    state = session.new_state(session.DEFAULTS)
    assert say(capsys, state, "source file x.png") == ["source file x.png"]
    assert say(capsys, state, 'source file "a b.png"') == ['source file "a b.png"']
    assert say(capsys, state, "source camera 2") == ["source camera 2"]
    assert say(capsys, state, "roi 0 0 20 10")[-1] == "roi 0 0 20 10"
    assert say(capsys, state, "roi full") == ["roi full"]


def test_show_follows_the_commands(capsys, tmp_path):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    registry.run_command(state, f'source file "{path.as_posix()}"')
    registry.run_command(state, "roi 0 0 20 10")
    registry.run_command(state, "step")
    capsys.readouterr()  # släng ekot och toppen
    rows = say(capsys, state, "show")
    assert f"källa: fil {path.as_posix()}" in rows
    assert "roi: 0 0 20 10" in rows
    assert "mätning: ja" in rows
