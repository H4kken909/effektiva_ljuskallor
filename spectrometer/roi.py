"""ROI-hjälp ur en bild: profilen tvärs spektrumet, bandet, ett ROI-förslag och riktningen. Ren NumPy; vet inget om state."""

import numpy as np

from spectrometer import calc


def cross_profile(image, axis, channel):
    """Medel längs spektrumriktningen: ett tal per bildrad (horizontal) eller per kolumn (vertical), float64 i counts."""
    height, width = image.shape[:2]
    return calc.prepare(image, (0, 0, width, height), axis, channel).mean(axis=1)


def background(values):
    """Bakgrunden: medianen (bandet är smalt, så de flesta rader är mörka)."""
    return float(np.median(values))


def find_band(profile, fraction=0.5):
    """Sammanhängande stycke runt största värdet där profilen är över bakgrund + fraction · (topp - bakgrund).

    Returnerar: (start, längd) i index, eller None när profilen är platt (inget band).
    """
    i = int(np.argmax(profile))
    low = background(profile)
    if profile[i] <= low:
        return None
    above = profile > low + fraction * (profile[i] - low)
    start, stop = i, i + 1
    while start > 0 and above[start - 1]:
        start -= 1
    while stop < len(profile) and above[stop]:
        stop += 1
    return start, stop - start


def band_roi(shape, axis, start, length):
    """ROI (x, y, w, h) över hela bilden längs spektrumet och length pixlar tvärs, från start."""
    height, width = shape[:2]
    return (0, start, width, length) if axis == "horizontal" else (start, 0, length, height)


def suggest(image, axis, channel):
    """ROI-förslag ur bandet vid halva höjden (find_band); None när bilden inte har något band."""
    band = find_band(cross_profile(image, axis, channel))
    return None if band is None else band_roi(image.shape, axis, *band)


def detect_axis(image, channel):
    """Bandets riktning ur de ljusa pixlarnas omslutande rektangel: (axis, bredd, höjd) i pixlar, eller None."""
    height, width = image.shape[:2]
    table = calc.prepare(image, (0, 0, width, height), "horizontal", channel)
    low = background(table)
    if table.max() <= low:
        return None
    rows, cols = np.nonzero(table > low + 0.5 * (table.max() - low))
    wide, high = int(cols.max() - cols.min() + 1), int(rows.max() - rows.min() + 1)
    return ("horizontal" if wide >= high else "vertical"), wide, high
