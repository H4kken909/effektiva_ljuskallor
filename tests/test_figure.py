"""1.2.5 figure: rapportfigur som PNG eller SVG utan fönster, med UT.txt till bildtexten."""

import cv2
import matplotlib.pyplot as plt
import pytest
from test_compare import two_folders
from test_elias import line_image, new_state

from spectrometer import registry


def measured(tmp_path, *lines):
    """Linjebilden som källa, raderna i lines och step. Ger state."""
    path = tmp_path / "bild.png"
    cv2.imwrite(str(path), line_image())
    state = new_state()
    for line in (f"source file {path.as_posix()}", *lines, "step"):
        registry.run_command(state, line)
    return state


def test_figure_of_the_latest_measurement(tmp_path, capsys):
    """PNG utan pyplot-fönster, och UT.txt med axlarna, villkoren och förbehållet."""
    state = measured(tmp_path)
    before = plt.get_fignums()
    target = tmp_path / "fig-01.png"
    registry.run_command(state, f"figure {target.as_posix()}")
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert plt.get_fignums() == before
    caption = (tmp_path / "fig-01.txt").read_text(encoding="utf-8").splitlines()
    assert caption[0] == "Figur fig-01.png: x pixel, y signal (counts)"
    assert caption[1].startswith("senaste mätningen: mapp inte sparad, mätt okänt, kanal gray, frames 1, läge direct")
    assert caption[2] == "Relativa tal från kameran; inte watt, lumen eller verkningsgrad."
    assert capsys.readouterr().out.splitlines()[-1].startswith(f"Sparad: {target.as_posix()} och ")


def test_figure_svg_of_folders_with_options(tmp_path):
    """Mapparna i samma axlar som SVG, normerade, med --xlim och --log; villkoren ur settings.json."""
    folders = two_folders(tmp_path)
    target = tmp_path / "jamfor.svg"
    registry.run_command(new_state(), f"figure {target.as_posix()} {' '.join(folders)} --norm --xlim 5 15 --log")
    assert "<svg" in target.read_text(encoding="utf-8")
    caption = (tmp_path / "jamfor.txt").read_text(encoding="utf-8").splitlines()
    assert caption[0] == "Figur jamfor.svg: x pixel, y normerad signal (relativ, bara visning), logaritmisk y"
    assert caption[1].startswith(f"stark: mapp {folders[0]}, mätt 20")


def test_figure_ev_and_bad_words(tmp_path):
    """--ev kräver nm; efter calibrate går det. Fel första ord, fel --xlim och okänd flagga ger input-fel."""
    state = measured(tmp_path)
    with pytest.raises(ValueError, match="kräver våglängd i nm"):
        registry.run_command(state, f"figure {(tmp_path / 'e.png').as_posix()} --ev")
    points = tmp_path / "p.csv"
    points.write_text("pixel,wavelength_nm,check\n0,400,0\n19,590,0\n", encoding="utf-8")
    state = measured(tmp_path, f"calibrate {points.as_posix()}")
    registry.run_command(state, f"figure {(tmp_path / 'e.png').as_posix()} --ev")
    assert (tmp_path / "e.txt").read_text(encoding="utf-8").startswith("Figur e.png: x fotonenergi (eV)")
    for line, text in (("figure ut.jpg", "UT.png eller UT.svg"), ("figure ut.png --xlim 5", "två tal"),
                       ("figure ut.png --xlim 9 1", "MIN mindre än MAX"), ("figure ut.png --titel", "okänd flagga")):
        with pytest.raises(ValueError, match=text):
            registry.run_command(state, line)
