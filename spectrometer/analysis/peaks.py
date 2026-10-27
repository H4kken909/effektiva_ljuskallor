import itertools

import numpy as np

from spectrometer.measurement import calc


def find_peaks(values, mask, min_fraction=0.05, min_distance=3, middle=False):
    if not mask.any():
        return []
    v = np.where(mask, values, np.nan)
    min_height = min_fraction * np.nanmax(v)
    found = []
    if middle:
        i = 0
        while i < len(v):
            if (i == 0 or v[i] > v[i - 1]) and v[i] >= min_height:
                j = i
                while j + 1 < len(v) and v[j + 1] == v[i]:
                    j += 1
                if (j + 1 == len(v) and i > 0) or (j + 1 < len(v) and v[j + 1] < v[i]):
                    found.append((i + j) // 2)
                i = j + 1
            else:
                i += 1
    else:
        y = np.where(mask, values, -np.inf)
        if np.all(y == y[0]):
            return []
        for i in range(len(y)):
            left = y[i - 1] if i > 0 else -np.inf
            right = y[i + 1] if i < len(y) - 1 else -np.inf
            if y[i] >= left and y[i] > right and y[i] >= min_height:
                found.append(i)
    kept = []
    for k in sorted(found, key=lambda k: -v[k]):
        if all(abs(k - other) >= min_distance for other in kept):
            kept.append(k)
    return kept


def refine_peak(values, i):
    if i <= 0 or i >= len(values) - 1:
        return float(i)
    left, top, right = values[i - 1], values[i], values[i + 1]
    if not np.all(np.isfinite([left, top, right])) or left == top or right == top:
        return float(i)
    return float(i + 0.5 * (left - right) / (left - 2 * top + right))


def match_peaks(peak_pixels, line_nm):
    pixels = np.sort(np.asarray(peak_pixels, dtype=np.float64))
    tried = []
    for chosen in itertools.combinations(np.sort(line_nm), pixels.size):
        chosen = np.array(chosen)
        fitted = calc.evaluate_wavelength(pixels, calc.fit_wavelength(pixels, chosen, 1))
        tried.append((float(np.sqrt(np.mean((chosen - fitted) ** 2))), chosen))
    tried.sort(key=lambda t: t[0])
    next_rms = tried[1][0] if len(tried) > 1 else float("inf")
    return tried[0][1], tried[0][0], next_rms


def centroid(x, y, i):
    lo, hi = max(i - 1, 0), min(i + 2, len(x))
    w = np.clip(y[lo:hi], 0, None)
    if np.sum(w) <= 0:
        return float(x[i])
    return float(np.sum(x[lo:hi] * w) / np.sum(w))


def foot(y, i, step):
    j = low = i
    while 0 <= j + step < len(y) and np.isfinite(y[j + step]):
        nxt = y[j + step]
        if nxt > y[i] or (nxt == y[i] and y[low] < y[i]):
            break
        j += step
        if nxt < y[low]:
            low = j
    return low


def fwhm(x, y, i):
    left, right = foot(y, i, -1), foot(y, i, 1)
    floor = min(y[left], y[right])
    if left == i or right == i or y[i] <= floor or max(y[left], y[right]) - floor >= (y[i] - floor) / 2:
        return float("nan")
    line = y[left] + (y[right] - y[left]) * (x - x[left]) / (x[right] - x[left])
    z = y - line
    half = z[i] / 2
    j = i
    while z[j - 1] > half:
        j -= 1
    low = x[j - 1] + (half - z[j - 1]) * (x[j] - x[j - 1]) / (z[j] - z[j - 1])
    j = i
    while z[j + 1] > half:
        j += 1
    high = x[j] + (z[j] - half) * (x[j + 1] - x[j]) / (z[j] - z[j + 1])
    return float(high - low)


def area(x, y, mask):
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(y[mask], x[mask]))
