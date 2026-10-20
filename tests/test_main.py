"""Testar att measure ger rätt spektrum utan fönster"""

import cv2
import numpy as np

from spectrometer import measure, session


def state_for(folder):
    image = np.zeros((10, 20, 3), dtype="uint8")
    image[:, 12] = 200
    cv2.imwrite(str(folder / "bild.png"), image)
    state = session.new_state(session.DEFAULTS)
    state["settings"]["source"] = ("file", folder / "bild.png")
    return state


def test_measure_peak(tmp_path):
    state = state_for(tmp_path)
    spectrum = measure.measure(state)
    expected = np.zeros(20)
    expected[12] = 200
    np.testing.assert_allclose(spectrum["values"], expected)
    np.testing.assert_allclose(spectrum["x"], np.arange(20))
    assert np.all(spectrum["mask"])
    assert state["image"].shape == (10, 20, 3)