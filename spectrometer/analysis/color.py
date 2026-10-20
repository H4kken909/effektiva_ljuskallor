"""CIE 1931 2°: XYZ, xy och färgtemperatur ur ett spektrum. Kräver respons på; relativt, aldrig lumen."""

import numpy as np

# CIE 1931 2° färgmatchningsfunktioner, 380–780 nm i steg om 10 nm (x̄, ȳ, z̄). ȳ = V(λ).
_NM = np.arange(380, 781, 10, dtype=np.float64)
_X = np.array([0.0014, 0.0042, 0.0143, 0.0435, 0.1344, 0.2839, 0.3483, 0.3362, 0.2908, 0.1954, 0.0956, 0.0320, 0.0049,
               0.0093, 0.0633, 0.1655, 0.2904, 0.4334, 0.5945, 0.7621, 0.9163, 1.0263, 1.0622, 1.0026, 0.8544, 0.6424,
               0.4479, 0.2835, 0.1649, 0.0874, 0.0468, 0.0227, 0.0114, 0.0058, 0.0029, 0.0014, 0.0007, 0.0003, 0.0002,
               0.0001, 0.0000])
_Y = np.array([0.0000, 0.0001, 0.0004, 0.0012, 0.0040, 0.0116, 0.0230, 0.0380, 0.0600, 0.0910, 0.1390, 0.2080, 0.3230,
               0.5030, 0.7100, 0.8620, 0.9540, 0.9950, 0.9950, 0.9520, 0.8700, 0.7570, 0.6310, 0.5030, 0.3810, 0.2650,
               0.1750, 0.1070, 0.0610, 0.0320, 0.0170, 0.0082, 0.0041, 0.0021, 0.0010, 0.0005, 0.0003, 0.0001, 0.0001,
               0.0000, 0.0000])
_Z = np.array([0.0065, 0.0201, 0.0679, 0.2074, 0.6456, 1.3856, 1.7471, 1.7721, 1.6692, 1.2876, 0.8130, 0.4652, 0.2720,
               0.1582, 0.0782, 0.0422, 0.0203, 0.0087, 0.0039, 0.0021, 0.0017, 0.0011, 0.0008, 0.0003, 0.0002, 0.0000,
               0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
               0.0000, 0.0000])
WARM_WHITE = (0.45, 0.41)  # SUB1: varmt vitt
COOL_WHITE = (0.31, 0.32)  # SUB1: kallt vitt


def xyz(x_nm, values, mask):
    """Tristimulus X, Y, Z (relativa) ur ett spektrum i nm; bara giltiga positioner räknas."""
    sel = mask & np.isfinite(values) & (x_nm >= 380) & (x_nm <= 780)
    if np.count_nonzero(sel) < 2:
        raise ValueError("input.missing_data: för få giltiga positioner mellan 380 och 780 nm")
    lam, s = x_nm[sel], np.clip(values[sel], 0, None)
    cmf = [np.interp(lam, _NM, c) for c in (_X, _Y, _Z)]
    return tuple(float(np.trapezoid(c * s, lam)) for c in cmf)


def xy(X, Y, Z):
    """Kromaticitet x, y."""
    tot = X + Y + Z
    if tot <= 0:
        raise ValueError("input.missing_data: inget ljus (X+Y+Z = 0)")
    return X / tot, Y / tot


def cct_mccamy(x, y):
    """Färgtemperatur i K enligt McCamy (1992); giltig ungefär 2000–12500 K nära Planck-kurvan."""
    n = (x - 0.3320) / (0.1858 - y)
    return 449.0 * n**3 + 3525.0 * n**2 + 6823.3 * n + 5520.33


def luminous_rel(x_nm, values, mask):
    """Relativ ljusstyrka Σ V(λ)·S(λ): jämförbar mellan mätningar, aldrig lumen."""
    return xyz(x_nm, values, mask)[1]


def distance(p, q):
    """Avstånd i xy-planet."""
    return float(np.hypot(p[0] - q[0], p[1] - q[1]))


C2 = 1.4388e7  # nm·K, andra strålningskonstanten i Plancks lag
MCCAMY_K = (2000, 12500)  # där McCamy ungefär gäller
UV_MAX = 0.05  # längre från svartkroppskurvan än så i (u, v): ingen färgtemperatur (Ohno 2014: CCT saknar mening där)
MIN_COVERAGE = 0.95  # mindre av x̄, ȳ och z̄ inom mätningen än så: varning


def planck(x_nm, kelvin):
    """Svartkroppsstrålning vid kelvin K, relativ: λ^-5 / (e^(c2/(λT)) − 1). För tester, färgtemperatur och mix --cct."""
    lam = np.asarray(x_nm, dtype=np.float64)
    return lam**-5 / np.expm1(C2 / (lam * kelvin))


def planck_xy(kelvin):
    """Punkten (x, y) på svartkroppskurvan vid kelvin K."""
    lam = np.arange(380.0, 781.0)
    return xy(*xyz(lam, planck(lam, kelvin), np.ones(lam.size, dtype=bool)))


def uv(x, y):
    """CIE 1960 (u, v) ur x, y: där är avstånd till svartkroppskurvan jämförbara."""
    d = -2 * x + 12 * y + 3
    return 4 * x / d, 6 * y / d


def cct_line(x, y):
    """Raden om färgtemperaturen: McCamy när punkten ligger nära svartkroppskurvan, annars ingen (en färgad LED)."""
    cct = cct_mccamy(x, y)
    if not MCCAMY_K[0] <= cct <= MCCAMY_K[1]:
        return f"färgtemperatur: ingen (McCamy gäller bara {MCCAMY_K[0]}–{MCCAMY_K[1]} K)"
    gap = distance(uv(x, y), uv(*planck_xy(cct)))  # ungefär |Duv|, inte Ohnos metod
    if gap > UV_MAX:
        return f"färgtemperatur: ingen (avståndet till svartkroppskurvan är {gap:.3f} i uv, gränsen {UV_MAX})"
    return f"färgtemperatur: {cct:.0f} K (McCamy; avstånd till svartkroppskurvan {gap:.4f} i uv)"


def coverage(x_nm, mask):
    """Minsta andelen av x̄, ȳ och z̄ mellan första och sista giltiga position; 1,0 när hela 380–780 nm är mätt."""
    lam = np.arange(380.0, 781.0)
    valid = x_nm[mask]
    inside = (lam >= valid.min()) & (lam <= valid.max())
    shares = []
    for cmf in (_X, _Y, _Z):
        weight = np.interp(lam, _NM, cmf)
        shares.append(weight[inside].sum() / weight.sum())
    return float(min(shares))


def report(x_nm, values, mask):
    """Raderna som color skriver: xy, färgtemperatur, avstånd till SUB1:s vitpunkter, täckning och ljusstyrka.

    En rad som börjar med "Varning: " är en varning. Fel: ValueError med input.missing_data (ur xyz och xy).
    """
    X, Y, Z = xyz(x_nm, values, mask)
    x, y = xy(X, Y, Z)
    lines = [f"färg: x {x:.4f}  y {y:.4f}  (CIE 1931 2°)", cct_line(x, y)]
    for name, point in (("varmt vitt", WARM_WHITE), ("kallt vitt", COOL_WHITE)):
        lines.append(f"avstånd till {name} {point}: {distance((x, y), point):.4f}")
    share = coverage(x_nm, mask & np.isfinite(values))
    lines.append(f"täckning: {100 * share:.1f} % av x̄, ȳ och z̄ inom det mätta intervallet")
    if share < MIN_COVERAGE:
        lines.append("Varning: en del av spektrumet saknas (täckning under 95 %), x och y kan vara fel")
    lines.append(f"ljusstyrka (V(λ)-vägd, relativ): {Y:.4g}, jämför bara mätningar med samma inställningar")
    return lines


# mix --sweep: sRGB:s hörn (IEC 61966-2-1, D65), deras blandningar två och två, och SUB1:s vitpunkter
TARGETS = {"röd": (0.64, 0.33), "gul": (0.4193, 0.5053), "grön": (0.30, 0.60), "cyan": (0.2247, 0.3287),
           "blå": (0.15, 0.06), "magenta": (0.3209, 0.1542), "varmt vitt": WARM_WHITE, "kallt vitt": COOL_WHITE}


def weights(primaries, target):
    """Vikterna som blandar tre spektrum (deras X, Y, Z i kolumnerna) till färgen target = (x, y), största vikten 1.

    Minsta kvadrat på M·w = (x/y, 1, (1 − x − y)/y), alltså Y satt till 1; med tre LED är lösningen exakt.
    En negativ vikt betyder att target ligger utanför triangeln: de tre räcker inte.
    """
    x, y = target
    goal = np.array([x / y, 1.0, (1 - x - y) / y])
    w = np.linalg.lstsq(np.asarray(primaries, dtype=np.float64), goal, rcond=None)[0]
    return w / np.max(np.abs(w))


def gaussian(x_nm, center, fwhm):
    """En gaussisk linje med toppen 1 vid center nm och bredden fwhm nm: en simulerad LED (mix --fwhm)."""
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return np.exp(-0.5 * ((np.asarray(x_nm, dtype=np.float64) - center) / sigma) ** 2)


def triangle_area(points):
    """Arean av triangeln med hörnen points, tre (x, y), i xy-planet (skosnöreformeln)."""
    (x1, y1), (x2, y2), (x3, y3) = points
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2
