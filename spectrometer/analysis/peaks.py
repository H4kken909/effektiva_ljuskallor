"""Toppar, linjebredd och area ur ett spektrum. Ren NumPy; vet inget om state eller filer."""

import numpy as np

MIN_FRACTION = 0.05  # en topp ska vara minst så stor andel av högsta värdet
MIN_DISTANCE = 3  # toppar närmare än så (punkter) slås ihop till den högsta


def find_peaks(y, mask):
    """Lokala maxima över MIN_FRACTION·max, minst MIN_DISTANCE punkter isär. Ger index, störst först."""
    yy = np.where(mask, y, -np.inf)
    if len(yy) and np.all(yy == yy[0]):
        return []  # helt platt kurva: ingen topp, inte heller i sista pixeln
    finite = yy[np.isfinite(yy)]
    limit = MIN_FRACTION * (finite.max() if finite.size else 0.0)
    # Utanför kanten räknas som lägre: första och sista pixeln kan vara toppar.
    around = np.pad(yy, 1, constant_values=-np.inf)
    hits = []
    for i in range(len(yy)):
        if around[i + 1] >= around[i] and around[i + 1] > around[i + 2] and yy[i] >= limit and np.isfinite(yy[i]):
            hits.append(i)
    hits.sort(key=lambda i: -yy[i])
    kept = []
    for i in hits:
        if all(abs(i - j) >= MIN_DISTANCE for j in kept):
            kept.append(i)
    return kept


def centroid(x, y, i):
    """Toppens läge som tyngdpunkt över tre punkter (sub-pixel)."""
    lo, hi = max(i - 1, 0), min(i + 2, len(x))
    w = np.clip(y[lo:hi], 0, None)
    total = np.sum(w)
    return float(np.sum(x[lo:hi] * w) / total) if total > 0 else float(x[i])


def bases(y, i):
    """Toppens baspunkter (vänster, höger): lägsta punkten på var sida innan nästa lika höga topp.

    Som prominensen i katalogen: gå från toppen åt var sida tills ett högre värde, en lucka (NaN) eller kanten
    kommer, och ta den lägsta punkten på vägen. Ett lika högt värde efter en dal är också en annan topp; en platå vid
    toppen (samma tal i rad, vanligt med 8 bitar) är det inte. Brus på flanken stoppar alltså inte sökningen.
    """
    found = []
    for step in (-1, 1):
        j = low = i
        while 0 <= j + step < len(y) and np.isfinite(y[j + step]):
            following = y[j + step]
            if following > y[i] or (following == y[i] and y[low] < y[i]):
                break
            j += step
            if following < y[low]:
                low = j
        found.append(low)
    return found[0], found[1]


def width(x, y, i, saturated=None):
    """FWHM över en rak baslinje mellan toppens baspunkter, som rev7: (bredd, None) eller (NaN, orsak).

    Baslinjen dras mellan baspunkterna (bases) och dras av; halva höjden är halva toppens höjd över baslinjen, och
    korsningarna interpoleras linjärt på var sida. Ogiltig (rev7: inget tal hellre än ett påhittat) när toppen är
    mättad (saturated sant mellan baspunkterna) och när kurvan inte går ner till halva höjden på båda sidor: toppen
    vid kanten, en lucka eller en topp intill med dalen över halva höjden.
    """
    if not np.isfinite(y[i]):
        return float("nan"), "okänd (ingen topp)"
    left, right = bases(y, i)
    floor = min(y[left], y[right])
    height = y[i] - floor
    if left == i or right == i or height <= 0 or max(y[left], y[right]) - floor >= height / 2:
        return float("nan"), "okänd (kurvan når inte halva höjden)"
    if saturated is not None and np.any(saturated[left:right + 1]):
        return float("nan"), "ogiltig (toppen är mättad)"
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
    return float(high - low), None


def fwhm(x, y, i):
    """Full bredd vid halva höjden över baslinjen kring index i (bara bredden ur width); NaN om den är ogiltig."""
    return width(x, y, i)[0]


def area(x, y, mask):
    """Trapetsarea under kurvan där masken är sann."""
    if np.count_nonzero(mask) < 2:
        return float("nan")
    return float(np.trapezoid(y[mask], x[mask]))


def fwhm_sigma(x, y, i, sigma):
    """Slumpfelet i fwhm(x, y, i) när varje position har osäkerheten sigma (oberoende), till första ordningen.

    Varje position nära toppen flyttas lite upp och ner; ändringen i FWHM gånger sigma är dess bidrag, och bidragen
    läggs ihop i kvadrat. Ger NaN när FWHM saknas eller sigma saknas där den behövs. Bara slumpbruset: kalibrering
    och instrumentets bredd ingår inte.
    """
    full = fwhm(x, y, i)
    if not np.isfinite(full):
        return float("nan")
    reach = full + 2 * float(np.median(np.abs(np.diff(x))))  # korsningarna och punkterna bredvid dem
    total = 0.0
    for k in np.flatnonzero(np.abs(x - x[i]) <= reach):
        if not np.isfinite(y[k]):
            continue
        if not np.isfinite(sigma[k]):
            return float("nan")
        if sigma[k] == 0:
            continue
        step = 1e-3 * sigma[k]
        up, down = y.copy(), y.copy()
        up[k] += step
        down[k] -= step
        total += ((fwhm(x, up, i) - fwhm(x, down, i)) / (2 * step) * sigma[k]) ** 2
    return float(np.sqrt(total))
