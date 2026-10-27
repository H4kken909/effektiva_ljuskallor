import numpy as np

_NM = np.arange(380, 781, 10, dtype=np.float64)
_X = np.array([0.0014, 0.0042, 0.0143, 0.0435, 0.1344, 0.2839, 0.3483, 0.3362, 0.2908, 0.1954, 0.0956, 0.0320, 0.0049, 0.0093,
               0.0633, 0.1655, 0.2904, 0.4334, 0.5945, 0.7621, 0.9163, 1.0263, 1.0622, 1.0026, 0.8544, 0.6424, 0.4479, 0.2835,
               0.1649, 0.0874, 0.0468, 0.0227, 0.0114, 0.0058, 0.0029, 0.0014, 0.0007, 0.0003, 0.0002, 0.0001, 0.0000])
_Y = np.array([0.0000, 0.0001, 0.0004, 0.0012, 0.0040, 0.0116, 0.0230, 0.0380, 0.0600, 0.0910, 0.1390, 0.2080, 0.3230, 0.5030,
               0.7100, 0.8620, 0.9540, 0.9950, 0.9950, 0.9520, 0.8700, 0.7570, 0.6310, 0.5030, 0.3810, 0.2650, 0.1750, 0.1070,
               0.0610, 0.0320, 0.0170, 0.0082, 0.0041, 0.0021, 0.0010, 0.0005, 0.0003, 0.0001, 0.0001, 0.0000, 0.0000])
_Z = np.array([0.0065, 0.0201, 0.0679, 0.2074, 0.6456, 1.3856, 1.7471, 1.7721, 1.6692, 1.2876, 0.8130, 0.4652, 0.2720, 0.1582,
               0.0782, 0.0422, 0.0203, 0.0087, 0.0039, 0.0021, 0.0017, 0.0011, 0.0008, 0.0003, 0.0002, 0.0000, 0.0000, 0.0000,
               0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000])
WARM_WHITE = (0.45, 0.41)
COOL_WHITE = (0.31, 0.32)


def xyz(x_nm, values, mask):
    ok = mask & np.isfinite(values) & (x_nm >= 380) & (x_nm <= 780)
    if np.count_nonzero(ok) < 2:
        raise ValueError("too few valid positions between 380 and 780 nm")
    lam, s = x_nm[ok], np.clip(values[ok], 0, None)
    return [float(np.trapezoid(np.interp(lam, _NM, cmf) * s, lam)) for cmf in (_X, _Y, _Z)]


def xy(X, Y, Z):
    if X + Y + Z <= 0:
        raise ValueError("no light (X+Y+Z = 0)")
    return X / (X + Y + Z), Y / (X + Y + Z)


def planck_xy(kelvin):
    lam = np.arange(380.0, 781.0)
    spectrum = lam**-5 / np.expm1(1.4388e7 / (lam * kelvin))
    return xy(*xyz(lam, spectrum, np.ones(lam.size, dtype=bool)))


def uv(x, y):
    d = -2 * x + 12 * y + 3
    return 4 * x / d, 6 * y / d


def cct_line(x, y):
    u, v = uv(x, y)
    grid = np.linspace(1e6 / 20000, 1e6 / 1000, 200)
    for turn in range(4):
        points = np.array([uv(*planck_xy(1e6 / mired)) for mired in grid])
        k = int(np.argmin(np.hypot(points[:, 0] - u, points[:, 1] - v)))
        if turn == 0:
            at_end = k in (0, grid.size - 1)
        best = grid[k], points[k]
        grid = np.linspace(grid[max(k - 1, 0)], grid[min(k + 1, grid.size - 1)], 21)
    mired, (u_t, v_t) = best
    duv = round(float(np.copysign(np.hypot(u - u_t, v - v_t), v - v_t)), 4) + 0.0
    if at_end:
        return "color temperature: none (closest to the blackbody curve outside 1000-20000 K)"
    if abs(duv) > 0.01:
        return f"color temperature: none (Duv {duv:+.4f} is more than 0.01 from the blackbody curve)"
    return f"color temperature: {1e6 / mired:.0f} K, Duv {duv:+.4f}"


def report(x_nm, values, mask):
    x, y = xy(*xyz(x_nm, values, mask))
    warm = np.hypot(x - WARM_WHITE[0], y - WARM_WHITE[1])
    cool = np.hypot(x - COOL_WHITE[0], y - COOL_WHITE[1])
    return [f"color: x {x:.4f}  y {y:.4f}  (CIE 1931 2°)", cct_line(x, y),
            f"distance to warm white {WARM_WHITE}: {warm:.4f}", f"distance to cool white {COOL_WHITE}: {cool:.4f}"]


def weights(primaries, target):
    x, y = target
    goal = np.array([x / y, 1.0, (1 - x - y) / y])
    w = np.linalg.lstsq(np.asarray(primaries, dtype=np.float64), goal, rcond=None)[0]
    return w / np.max(np.abs(w))
