"""1.0.37 Extraktionsval: median över raderna, binning, bakgrund bredvid bandet, rows och background."""

import cv2
import numpy as np
import pytest
from test_elias import error_text, new_state
from test_kedjan import ready
from test_metadata import saved_settings

from spectrometer import calc, registry


def band_image():
    """10 x 20: bakgrund 10 överallt, bandet i rad 4 och 5 är 110, och 210 i kolumn 12."""
    image = np.full((10, 20, 3), 10, dtype="uint8")
    image[4:6] = 110
    image[4:6, 12] = 210
    return image


def band_state(tmp_path):
    """State med bandbilden som källa och ROI:n på bandet (0 4 20 2), kanal red."""
    path = tmp_path / "band.png"
    cv2.imwrite(str(path), band_image())
    state = new_state()
    for line in (f"source file {path.as_posix()}", "roi 0 4 20 2", "channel red"):
        registry.run_command(state, line)
    return state


def test_extract_median():
    """ROI-14: medianen per kolumn tål ett avvikande värde; medlet (extract_spectrum) gör det inte."""
    table = np.array([[1.0, 2.0], [3.0, 100.0], [5.0, 6.0]])
    np.testing.assert_array_equal(calc.extract_median(table), [3.0, 6.0])
    np.testing.assert_array_equal(calc.extract_spectrum(table), [3.0, 36.0])


def test_side_background():
    """ROI-21: medianen av raderna ovanför och under, per kolumn; vid vertical kolumnerna bredvid; för lite plats ger fel."""
    image = band_image()
    np.testing.assert_array_equal(calc.side_background(image, (0, 4, 20, 2), 2, "red"), np.full(20, 10.0))
    turned = np.ascontiguousarray(image.transpose(1, 0, 2))
    np.testing.assert_array_equal(calc.side_background(turned, (4, 0, 2, 20), 2, "red", "vertical"), np.full(20, 10.0))
    with pytest.raises(ValueError, match="bakgrunden behöver 5 fria rader på båda sidor"):
        calc.side_background(image, (0, 4, 20, 2), 5, "red")


def test_rows_median_in_measure(tmp_path, capsys):
    """ROI-15: rows median ger medianen över ROI:ns rader; rows ensam visar valet."""
    image = band_image()
    image[3, 5] = 250  # en het pixel i översta raden av ROI:n nedan
    path = tmp_path / "het.png"
    cv2.imwrite(str(path), image)
    state = new_state()
    for line in (f"source file {path.as_posix()}", "roi 0 3 20 3", "channel red", "step"):
        registry.run_command(state, line)
    assert state["spectrum"]["values"][5] == pytest.approx((250 + 110 + 110) / 3)
    registry.run_command(state, "rows median")
    assert state["spectrum"] is None
    registry.run_command(state, "step")
    assert state["spectrum"]["values"][5] == 110
    capsys.readouterr()
    registry.run_command(state, "rows")
    assert capsys.readouterr().out == "rows: median\n"
    assert error_text(state, "rows max") == "input.invalid_argument: rows: okänt val max, välj mean eller median"


def test_background_command(tmp_path, capsys):
    """ROI-22: background N drar av bakgrunden efter mörkret; för många rader och fel ord ger fel; off stänger av."""
    state = band_state(tmp_path)
    registry.run_command(state, "step")
    registry.run_command(state, "background 2")
    capsys.readouterr()
    registry.run_command(state, "step")
    assert capsys.readouterr().out == "Topp 200 vid pixel 12 (1 bild)\n"
    assert error_text(state, "background 5") == (
        "input.invalid_argument: bakgrunden behöver 5 fria rader på båda sidor om roi (0, 4, 20, 2)"
    )
    assert state["background"] == 2
    assert error_text(state, "background 0") == "input.invalid_argument: N ska vara minst 1"
    registry.run_command(state, "background off")
    registry.run_command(state, "background")
    assert capsys.readouterr().out.splitlines()[-2:] == ["background: off", "background: off"]
    registry.run_command(state, "step")
    assert capsys.readouterr().out == "Topp 210 vid pixel 12 (1 bild)\n"


def test_background_without_image_is_checked_at_step(capsys):
    """Utan bild kontrolleras bakgrunden vid nästa mätning, som roi."""
    state = new_state()
    registry.run_command(state, "background 1")
    assert capsys.readouterr().out == "Bakgrunden kontrolleras vid nästa mätning.\nbackground: 1\n"


def test_rows_and_background_forget_response_and_reference(tmp_path, capsys):
    """Som roi och channel: respons och referens gjordes på det gamla sättet och glöms."""
    for line in ("rows median", "background 1"):
        state, _ = ready(tmp_path)
        capsys.readouterr()
        registry.run_command(state, line)
        rows = capsys.readouterr().out.splitlines()
        assert "Responsen glömd. Kör response build igen." in rows
        assert "Referensen glömd. Kör reference igen." in rows
        assert (state["response"], state["reference"]) == (None, None)


def test_settings_json_has_extraction(tmp_path):
    """settings.json får extraction (rows och background) före coefficients; slutet av filen är som förut."""
    settings, _ = saved_settings(tmp_path, ["rows median"])
    assert settings["extraction"] == {"rows": "median", "background": None}
    keys = list(settings)
    assert keys.index("extraction") < keys.index("settings_id") < keys.index("coefficients")
    assert keys[-4:] == ["coefficients", "dark", "use_response", "mode"]
