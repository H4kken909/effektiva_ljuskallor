"""roi.py och ROI-kommandona: profil, band, förslag, riktning, roi show, band och move, utan kamera."""

import cv2
import numpy as np

from spectrometer import registry, roi, session


def band_image(vertical=False):
    """En bild 20 x 30 med ett ljust band: rad 8-11 (vågrätt) eller kolumn 5-7 (lodrätt); en pixel är 255."""
    image = np.full((20, 30, 3), 3, dtype="uint8")
    if vertical:
        image[:, 5:8] = 180
    else:
        image[8:12, :] = 180
        image[9, 20] = 255
    return image


def state_with(tmp_path, image):
    """state med bilden som källa, en mätning gjord och output_dir i tmp."""
    path = tmp_path / "band.png"
    cv2.imwrite(str(path), image)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["output_dir"] = (tmp_path / "data").as_posix()
    registry.run_command(state, f"source file {path.as_posix()}")
    registry.run_command(state, "step")
    return state


def test_profil_och_band():
    image = band_image()
    profile = roi.cross_profile(image, "horizontal", "gray")
    assert profile.shape == (20,)
    assert roi.find_band(profile) == (8, 4)


def test_riktning():
    assert roi.detect_axis(band_image(), "gray") == ("horizontal", 30, 4)
    assert roi.detect_axis(band_image(vertical=True), "gray") == ("vertical", 3, 20)


def test_roi_auto_profile_och_axis_detect(tmp_path, capsys):
    state = state_with(tmp_path, band_image())
    capsys.readouterr()
    registry.run_command(state, "roi auto")
    registry.run_command(state, "roi profile")
    registry.run_command(state, "axis detect")
    assert capsys.readouterr().out.splitlines() == [
        "Förslag: roi 0 8 30 4 (kör raden för att godta)",
        "Bandets mitt: rad 9.5",
        "Bredd vid halva höjden: 4 rader",
        "Bakgrund: 3.0 counts, topp: 182.5",
        "Bandet verkar vara vågrätt (30 px brett, 4 px högt). Kör axis horizontal.",
    ]
    assert state["settings"]["roi"] is None


def test_roi_band_och_move(tmp_path, capsys):
    state = state_with(tmp_path, band_image())
    registry.run_command(state, "roi band 8 4")
    assert state["settings"]["roi"] == (0, 8, 30, 4)
    registry.run_command(state, "roi move 0 2")
    assert state["settings"]["roi"] == (0, 10, 30, 4)
    for line, start in (("roi move 0 100", "input.invalid_argument: roi (0, 110, 30, 4) ligger utanför"),
                        ("roi move -1 0", "input.invalid_argument: x ska vara minst 0")):
        try:
            registry.run_command(state, line)
        except ValueError as error:
            assert str(error).startswith(start)
        assert state["settings"]["roi"] == (0, 10, 30, 4)
    assert "roi 0 10 30 4" in capsys.readouterr().out  # ekot i kommandoform sedan 1.0.41


def test_roi_show_sparar_bilden_med_rutan(tmp_path, capsys):
    state = state_with(tmp_path, band_image())
    registry.run_command(state, "roi 0 8 30 4")
    registry.run_command(state, "step")
    capsys.readouterr()
    registry.run_command(state, "roi show")
    saved = list((tmp_path / "data").glob("roi-*.png"))
    assert len(saved) == 1
    assert capsys.readouterr().out == f"Sparad i {saved[0].as_posix()}\n"
    image = cv2.imread(str(saved[0]))
    assert tuple(image[8, 0]) == (0, 255, 0)
    assert tuple(image[9, 20]) == (255, 0, 255)


def test_roi_utan_bild():
    state = session.new_state(session.DEFAULTS)
    for line in ("roi show", "roi auto", "roi profile", "roi band 0 4", "axis detect"):
        try:
            registry.run_command(state, line)
        except ValueError as error:
            assert str(error) == "input.missing_data: Ingen bild än. Kör step först."
        else:
            raise AssertionError(line)


def test_roi_auto_med_fel_riktning(tmp_path):
    state = state_with(tmp_path, band_image(vertical=True))
    try:
        registry.run_command(state, "roi auto")
    except ValueError as error:
        assert str(error) == ("input.missing_data: inget ljust band tvärs spektrumet (axis horizontal). "
                              "Tänd lampan och kör step, eller prova axis detect.")
    else:
        raise AssertionError("roi auto gav inget fel")
