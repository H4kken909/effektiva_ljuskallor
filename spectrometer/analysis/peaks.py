"""Toppar, linjebredd och area ur ett spektrum. Ren NumPy; vet inget om state eller filer."""

import numpy as np


def find_peaks(x, y, mask, prominence=0.05, min_distance=3):
    """Lokala maxima över prominence·max, minst min_distance punkter isär. Ger index, störst först."""
    yy = np.where(mask, y, -np.inf)
    top = np.nanmax(yy[np.isfinite(yy)]) if np.any(np.isfinite(yy)) else 0.0
    hits = []
    for i in range(1, len(yy) - 1):
        if yy[i] >= yy[i - 1] and yy[i] > yy[i + 1] and yy[i] >= prominence * top and np.isfinite(yy[i]):
            hits.append(i)
    hits.sort(key=lambda i: -yy[i])
    kept = []
    for i in hits:
        if all(abs(i - j) >= min_distance for j in kept):
            kept.append(i)
    return kept


def centroid(x, y, i):
    """Toppens läge som tyngdpunkt över tre punkter (sub-pixel)."""
    lo, hi = max(i - 1, 0), min(i + 2, len(x))
    w = np.clip(y[lo:hi], 0, None)
    return float(np.sum(x[lo:hi] * w) / np.sum(w)) if np.sum(w) > 0 else float(x[i])


def fwhm(x, y, i):
    """Full bredd vid halva höjden kring index i, linjärt interpolerad. NaN om kurvan inte når ner."""
    half = y[i] / 2
    left = right = None
    for j in range(i, 0, -1):
        if y[j - 1] <= half:
            left = x[j - 1] + (half - y[j - 1]) * (x[j] - x[j - 1]) / (y[j] - y[j - 1])
            break
    for j in range(i, len(y) - 1):
        if y[j + 1] <= half:
            right = x[j] + (y[j] - half) * (x[j + 1] - x[j]) / (y[j] - y[j + 1])
            break
    return float(right - left) if left is not None and right is not None else float("nan")


def area(x, y, mask, lo=None, hi=None):
    """Trapetsarea under kurvan där masken är sann, valfritt mellan lo och hi i x-enheter."""
    sel = mask.copy()
    if lo is not None:
        sel &= x >= lo
    if hi is not None:
        sel &= x <= hi
    if np.count_nonzero(sel) < 2:
        return float("nan")
    return float(np.trapezoid(y[sel], x[sel]))
