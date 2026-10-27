import cv2
import numpy as np

SHIFT = 4
ONE = 1 << SHIFT
FAR = 1 << 12
HOT_SIGMA = 2.0
SOFT = 0.6


def rgb(colour):
    return np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def look(background, line, strokes, fill, fill_alpha):
    base = rgb(background)
    dark = base.mean() < 128
    sign = 1.0 if dark else -1.0
    acc = base.copy()
    outer = middle = inner = None
    outer_width = middle_width = inner_width = 0.0
    for colour, width, alpha in strokes:
        before = acc.copy()
        acc = acc + alpha * (rgb(colour) - acc)
        if width >= 14:
            outer, outer_width = acc - base, max(outer_width, width)
        elif width >= 5:
            middle, middle_width = acc - before, max(middle_width, width)
        else:
            inner, inner_width = acc, max(inner_width, width)

    def part(delta):
        return None if delta is None else tuple(np.clip(sign * delta, 0, 255)) + (0.0,)

    return {
        "add": dark,
        "outer": part(outer), "outer_sigma": outer_width / 5,
        "middle": part(middle), "middle_sigma": middle_width / 4,
        "inner": None if inner is None else tuple(np.clip(inner, 0, 255)) + (255.0,), "inner_width": inner_width,
        "fill": part(fill_alpha * (rgb(fill) - base)),
        "line": tuple(rgb(line)) + (255.0,),
    }


def runs(points, size, origin):
    x = points[:, 0] - origin[0] - 0.5
    y = origin[1] - points[:, 1] - 0.5
    good = np.isfinite(x) & np.isfinite(y)
    fixed = np.empty((len(x), 2), dtype=np.int32)
    fixed[:, 0] = np.rint(np.clip(np.nan_to_num(x), -FAR, size[0] + FAR) * ONE)
    fixed[:, 1] = np.rint(np.clip(np.nan_to_num(y), -FAR, size[1] + FAR) * ONE)
    edges = np.flatnonzero(np.diff(good.astype(np.int8)))
    starts = [0, *(edges + 1)]
    ends = [*(edges + 1), len(x)]
    return [fixed[a:b] for a, b in zip(starts, ends) if good[a]]


def _scaled(lines, factor):
    shift = (factor - 1) / 2 * ONE
    return [np.rint((line - shift) / factor).astype(np.int32) for line in lines]


def _glow_line(layer, lines, peak, sigma):
    strength = np.sqrt(2 * np.pi) * max(sigma, 0.5)
    colour = tuple(min(255.0, value * strength) for value in peak[:3]) + (0.0,)
    cv2.polylines(layer, lines, False, colour, 1, cv2.LINE_AA, SHIFT)


def glow(frame, background, lines, base_y, colours):
    height, width = frame.shape[:2]
    quarter = np.zeros(((height + 3) // 4, (width + 3) // 4, 4), np.uint8)
    half = np.zeros(((height + 1) // 2, (width + 1) // 2, 4), np.uint8)
    small = _scaled(lines, 4)
    if colours["outer"] is not None:
        sigma = colours["outer_sigma"] / 4
        _glow_line(quarter, small, colours["outer"], sigma)
        cv2.GaussianBlur(quarter, (0, 0), np.sqrt(max(sigma ** 2 - SOFT ** 2, 0.04)), dst=quarter)
    if colours["middle"] is not None:
        _glow_line(quarter, small, colours["middle"], max(colours["middle_sigma"] / 4, SOFT))
    if colours["outer"] is not None or colours["middle"] is not None:
        cv2.GaussianBlur(quarter, (0, 0), SOFT, dst=quarter)
        cv2.resize(quarter, (half.shape[1], half.shape[0]), dst=half, interpolation=cv2.INTER_LINEAR)
    if colours["fill"] is not None:
        base = int(round(base_y * ONE))
        area = np.zeros_like(half)
        polygons = [np.vstack([line, [[line[-1, 0], base], [line[0, 0], base]]]) for line in lines if len(line) > 1]
        if polygons:
            cv2.fillPoly(area, _scaled(polygons, 2), colours["fill"], cv2.LINE_8, SHIFT)
            cv2.add(half, area, dst=half)
    grown = cv2.resize(half, (2 * half.shape[1], 2 * half.shape[0]), interpolation=cv2.INTER_LINEAR)
    combine = cv2.add if colours["add"] else cv2.subtract
    combine(background, grown[:height, :width], dst=frame)
    if colours["inner"] is not None:
        reach = max(0.5, (colours["inner_width"] - 1) / 2)
        steps = max(1, int(np.ceil(reach - 0.25)))
        for step in range(1, steps + 1):
            d = int(round(reach * step / steps * ONE))
            for dx, dy in ((d, 0), (-d, 0), (0, d), (0, -d)):
                cv2.polylines(frame, [line + np.array([dx, dy], np.int32) for line in lines], False,
                              colours["inner"], 1, cv2.LINE_AA, SHIFT)


def curve(frame, lines, colours, scale=1.0):
    cv2.polylines(frame, lines, False, colours["line"], 1, cv2.LINE_AA, SHIFT)
    if scale >= 1.4 or colours["inner"] is None:
        half = int(round(0.5 * ONE))
        for dx, dy in ((half, 0), (0, half)) if scale >= 1.4 else ((0, half),):
            cv2.polylines(frame, [line + np.array([dx, dy], np.int32) for line in lines], False, colours["line"], 1,
                          cv2.LINE_AA, SHIFT)


def hot(frame, lines, ramp, colour, glow_alpha):
    rows = np.flatnonzero(ramp > 0)
    if not rows.size:
        return
    top, bottom = max(0, int(rows[0]) - 6), min(frame.shape[0], int(rows[-1]) + 7)
    band = frame[top:bottom]
    offset = np.array([0, top * ONE], dtype=np.int32)
    mask = np.zeros(band.shape[:2], np.uint8)
    cv2.polylines(mask, [line - offset for line in lines if len(line) > 1], False, 255, 1, cv2.LINE_AA, SHIFT)
    halo = cv2.GaussianBlur(mask, (0, 0), HOT_SIGMA)
    weight = ramp[top:bottom, None].astype(np.float32)
    shine = np.minimum(1.0, halo * np.float32(glow_alpha * np.sqrt(2 * np.pi) * HOT_SIGMA / 255)) * weight
    core = mask * (weight / 255)
    keep = (1 - shine) * (1 - core)
    target = np.asarray(colour, dtype=np.float32)
    band[..., :3] = np.rint(target + (band[..., :3] - target) * keep[..., None])


def stamp(frame, image, corner):
    rgba = image[::-1]
    alpha = rgba[..., 3:4].astype(np.float32) / 255
    premultiplied = np.zeros(rgba.shape, np.uint8)
    premultiplied[..., :3] = np.rint(rgba[..., :3] * alpha)
    inverse = np.full(rgba.shape, 255, np.uint8)
    inverse[..., :3] = 255 - rgba[..., 3:4]
    h, w = rgba.shape[:2]
    x0, y0 = corner
    a0, b0 = max(0, x0), max(0, y0)
    a1, b1 = min(frame.shape[1], x0 + w), min(frame.shape[0], y0 + h)
    if a1 <= a0 or b1 <= b0:
        return
    under = frame[b0:b1, a0:a1]
    cv2.multiply(under, inverse[b0 - y0:b1 - y0, a0 - x0:a1 - x0], dst=under, scale=1 / 255)
    cv2.add(under, premultiplied[b0 - y0:b1 - y0, a0 - x0:a1 - x0], dst=under)


def ring(frame, centre, radius, width, face, edge):
    x, y = (int(round(value * ONE)) for value in centre)
    r = int(round(radius * ONE))
    cv2.circle(frame, (x, y), r, tuple(face) + (255,), -1, cv2.LINE_AA, SHIFT)
    cv2.circle(frame, (x, y), r, tuple(edge) + (255,), max(1, int(round(width))), cv2.LINE_AA, SHIFT)


def line(frame, start, end, colour):
    if np.all(np.isfinite([*start, *end])):
        a = tuple(int(round(value * ONE)) for value in start)
        b = tuple(int(round(value * ONE)) for value in end)
        cv2.line(frame, a, b, tuple(colour) + (255,), 1, cv2.LINE_AA, SHIFT)
