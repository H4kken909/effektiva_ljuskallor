"""Tests that source reads an image file unchanged."""

import cv2
import numpy as np

from spectrometer import source

def test_read_image(tmp_path):
    bild = np.zeros((10, 20, 3), dtype="uint8")
    bild[:, 12] = 200

    path = tmp_path / "rand_x12.png"
    cv2.imwrite(str(path), bild)

    src = source.open_source("file", path)
    img = source.read_frame(src)
    source.close_source(src)
    assert img.shape == (10, 20, 3)
    assert img.dtype == "uint8"
    np.testing.assert_array_equal(img, bild)