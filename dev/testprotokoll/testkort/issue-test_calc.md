Uppgift 5: tests/test_calc.py, skriven efter guiden (0.1.3 del 11 till 14) med talen från mina testkort RX01, RX02 och RX05.

Tagg: v0.3.3beta2
python -m pytest tests/test_calc.py -v: test_rx05, test_rx02 och test_rx01_gray PASSED (3 passed in 0.36s)
ruff check .: All checks passed!
Rött med flit: 53 i stället för 52 i test_rx05 gav 1 failed, 2 passed. Med 52 igen: 3 passed.

Filen är inte committad. Lägg in den som tests/test_calc.py:

```python
"""Testar calc med räkneexemplen RX01, RX02 och RX05 från rev7."""

import numpy as np

from spectrometer import calc


def test_rx05():
    table = np.array([[10, 28, 50], [12, 32, 54]], dtype="float64")
    result = calc.extract_spectrum(table)
    np.testing.assert_allclose(result, [11, 30, 52], rtol=1e-9, atol=1e-9)


def test_rx02():
    image = np.zeros((2, 103, 3), dtype="uint8")
    image[0:2, 100:103, 2] = [[40, 255, 10], [42, 200, 12]]
    result_h = calc.prepare(image, (100, 0, 3, 2), "horizontal", "red")
    assert result_h.shape == (2, 3)
    np.testing.assert_array_equal(result_h, [[40, 255, 10], [42, 200, 12]])
    result_v = calc.prepare(image, (100, 0, 3, 2), "vertical", "red")
    assert result_v.shape == (3, 2)
    np.testing.assert_array_equal(result_v, [[40, 42], [255, 200], [10, 12]])


def test_rx01_gray():
    image = np.array([[[50, 100, 200]]], dtype="uint8")
    result = calc.prepare(image, (0, 0, 1, 1), "horizontal", "gray")
    np.testing.assert_allclose(result, 124.2, rtol=1e-9, atol=1e-9)
```
