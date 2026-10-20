"""Tester för quality.py: mättnad räknas bara i kanalerna som bidrar."""

import numpy as np

from spectrometer import quality


def two_pixels():
    """En bild 2 x 3: blå mättad i (0, 0), röd mättad i (1, 2), resten 100."""
    image = np.full((2, 3, 3), 100, dtype="uint8")
    image[0, 0, 0] = 255  # blå (BGR: index 0)
    image[1, 2, 2] = 255  # röd (index 2)
    return image


def test_saturated_count_per_channel():
    image = two_pixels()
    assert quality.saturated_count(image, "red") == 1
    assert quality.saturated_count(image, "blue") == 1
    assert quality.saturated_count(image, "green") == 0
    assert quality.saturated_count(image, "gray") == 2
    assert quality.saturated_count(image, "sum") == 2


def test_saturated_positions_follow_axis():
    image = two_pixels()
    np.testing.assert_array_equal(quality.saturated_positions(image, "horizontal", "red"), [False, False, True])
    np.testing.assert_array_equal(quality.saturated_positions(image, "vertical", "gray"), [True, True])


def test_crop_is_the_roi():
    image = two_pixels()
    assert quality.saturated_count(quality.crop(image, (0, 0, 2, 2)), "red") == 0
    assert quality.crop(image, None) is image