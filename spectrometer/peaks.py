"""Toppar i ett spektrum för kalibreringen: lokala maxima, toppläge med delpixel och parning mot kända linjer.

Ren NumPy; vet inget om state eller filer. Inte samma sak som analysis/peaks.py (linjebredd och area, 1.2.x).
"""

import itertools

import numpy as np

from spectrometer import calc


def find_peaks(values, mask, min_height, min_distance):
    """Index för lokala maxima bland giltiga positioner, högsta toppen först.

    En topp är v[i] > v[i-1] och v[i] >= v[i+1], minst min_height. En platå (mättad topp, samma värde flera
    positioner i rad) ger en topp i mitten. Toppar närmare än min_distance positioner slås ihop till den högsta.
    Parametrar: values: spektrumet, (P,) float64; mask: (P,) bool, True där värdet duger;
    min_height: lägsta topphöjd, samma enhet som values; min_distance: minsta avstånd i positioner (heltal).
    Returnerar: lista med index (int), högsta först; tom lista om ingen topp finns.
    """
    v = np.where(mask, values, np.nan)  # NaN jämför alltid falskt: ogiltiga positioner blir aldrig toppar
    found = []
    i = 1
    while i < len(v) - 1:
        if v[i] > v[i - 1] and v[i] >= min_height:
            j = i
            while j + 1 < len(v) and v[j + 1] == v[i]:
                j += 1  # platå: samma värde i rad
            if j + 1 < len(v) and v[j + 1] < v[i]:
                found.append((i + j) // 2)
            i = j + 1
        else:
            i += 1
    found.sort(key=lambda k: -v[k])
    kept = []
    for k in found:
        if all(abs(k - other) >= min_distance for other in kept):
            kept.append(k)
    return kept


def refine_peak(values, i):
    """Toppläget som flyttal: en parabel genom positionerna i-1, i och i+1.

    En platå (mättad topp), en kant eller en ogiltig granne ger i som det är, utan parabel.
    Parametrar: values: spektrumet, (P,) float64 (NaN där det är ogiltigt); i: toppens index från find_peaks.
    Returnerar: läget som float, i positioner (index), mellan i - 0.5 och i + 0.5.
    """
    if i <= 0 or i >= len(values) - 1:
        return float(i)
    left, top, right = values[i - 1], values[i], values[i + 1]
    if not np.all(np.isfinite([left, top, right])) or left == top or right == top:
        return float(i)
    # Parabelns topp: i + (vänster - höger) / (2 · (vänster - 2·topp + höger)).
    return float(i + 0.5 * (left - right) / (left - 2 * top + right))


def match_peaks(peak_pixels, line_nm):
    """Föreslår vilken linje varje topp är: alla ordningsbevarande val av linjerna, grad 1, minst rms vinner.

    Med 4 toppar och 5 linjer prövas 5 val (en linje utelämnas i taget), till exempel när gula dubbletten
    576.960 och 579.066 nm smälter ihop till en topp. Båda sorteras stigande, så spridningen (nm per pixel) är positiv.
    Parametrar: peak_pixels: topparnas pixlar i hela bilden, (K,); line_nm: linjernas våglängder i nm, (L,), K <= L.
    Returnerar: (chosen, rms, next_rms): chosen, (K,) float64, linjen i nm för varje topp i stigande pixel;
    rms: bästa valets rms-avvikelse i nm; next_rms: näst bästa valets (inf om det bara fanns ett val).
    """
    pixels = np.sort(np.asarray(peak_pixels, dtype=np.float64))
    lines = np.sort(np.asarray(line_nm, dtype=np.float64))
    tried = []
    for subset in itertools.combinations(lines, pixels.size):
        chosen = np.array(subset)
        fitted = calc.evaluate_wavelength(pixels, calc.fit_wavelength(pixels, chosen, 1))
        tried.append((float(np.sqrt(np.mean((chosen - fitted) ** 2))), chosen))
    tried.sort(key=lambda t: t[0])
    next_rms = tried[1][0] if len(tried) > 1 else float("inf")
    return tried[0][1], tried[0][0], next_rms
