import math

PINK = (255, 47, 168)
HOT = (255, 92, 207)
PURPLE = (157, 107, 255)
VIOLET = (196, 161, 255)
BEAM = (255, 250, 240)
DARK = (13, 10, 20)


def spectral(nm):
    if nm < 440:
        rgb = (-(nm - 440) / 60, 0.0, 1.0)
    elif nm < 490:
        rgb = (0.0, (nm - 440) / 50, 1.0)
    elif nm < 510:
        rgb = (0.0, 1.0, -(nm - 510) / 20)
    elif nm < 580:
        rgb = ((nm - 510) / 70, 1.0, 0.0)
    elif nm < 645:
        rgb = (1.0, -(nm - 645) / 65, 0.0)
    else:
        rgb = (1.0, 0.0, 0.0)
    edge = 0.35 + 0.65 * (nm - 380) / 40 if nm < 420 else 0.35 + 0.65 * (780 - nm) / 80 if nm > 700 else 1.0
    return tuple(round(255 * (max(0.0, value) * edge) ** 0.8) for value in rgb)


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def render(width, height, aspect, apex, reach):
    cols, rows = max(20, width), max(8, height)
    W, H = float(cols), rows * aspect
    cells = {}

    def put(col, row, char, rgb, power=1.0, heavy=False):
        if 0 <= col < cols and 0 <= row < rows:
            cells[col, row] = (char, rgb, power, heavy)

    height = H * 0.76
    top = H * 0.08
    centre = min(max(int(apex), 1), cols - 2) + 0.5
    half = height / math.sqrt(3)
    room = 2 * min(centre, W - centre)
    if half * 2 > room * 0.62:
        half = room * 0.31
        height = half * math.sqrt(3)
        top = (H - height) * 0.4
    bottom = top + height
    a, b, c = (centre, top), (centre - half, bottom), (centre + half, bottom)
    entry = (centre - half * 0.48, top + height * 0.48)
    exit_top = (centre + half * 0.36, top + height * 0.36)
    exit_bottom = (centre + half * 0.64, top + height * 0.64)
    end_x = min(W - 1.0, centre + reach)
    start_x = max(0.0, centre - reach)
    end_top, end_bottom = top + height * 0.40, min(H - 0.5, top + height * 1.04)

    for row in range(rows):
        y = (row + 0.5) * aspect
        for col in range(cols):
            x = col + 0.5
            if not exit_top[0] <= x <= end_x or x < centre + (y - top) / math.sqrt(3):
                continue
            along = (x - exit_top[0]) / (end_x - exit_top[0])
            upper = exit_top[1] + along * (end_top - exit_top[1])
            lower = exit_bottom[1] + (x - exit_bottom[0]) / (end_x - exit_bottom[0]) * (end_bottom - exit_bottom[1])
            if not upper <= y <= lower:
                continue
            f = (y - upper) / max(lower - upper, 1e-6)
            colour = mix(spectral(690 - f * 285), (255, 255, 255), 0.12 + 0.45 * max(0.0, 1 - along / 0.12))
            edge = min(1.0, 5 * min(f, 1 - f) + 0.3)
            fade = min(1.0, (end_x - x) / max(3.0, (end_x - start_x) * 0.06))
            power = edge * fade * (1.0 - 0.45 * along)
            put(col, row, "*" if power > 0.3 else ":", mix(DARK, colour, 0.25 + 0.75 * power), power * 0.7,
                power > 0.72)

    for i in range(4):
        target = (exit_top[0] + (exit_bottom[0] - exit_top[0]) * i / 3,
                  exit_top[1] + (exit_bottom[1] - exit_top[1]) * i / 3)
        n = max(1, int(max(abs(target[0] - entry[0]), abs(target[1] - entry[1]) / aspect)))
        for j in range(n + 1):
            t = j / n
            put(int(entry[0] + (target[0] - entry[0]) * t), int((entry[1] + (target[1] - entry[1]) * t) / aspect), ".",
                mix(DARK, mix(BEAM, VIOLET, t), 0.22 + 0.22 * t), 0.0)

    def face(t):
        return mix(HOT, PINK, t * 2) if t < 0.5 else mix(PINK, PURPLE, (t - 0.5) * 2 * 0.85)

    for (x0, y0), (x1, y1), char in ((a, b, "/"), (a, c, "\\")):
        for row in range(int(y0 / aspect), int(y1 / aspect) + 1):
            ya, yb = max(y0, row * aspect), min(y1, (row + 1) * aspect)
            if yb < ya:
                continue
            xa = x0 + (x1 - x0) * (ya - y0) / (y1 - y0)
            xb = x0 + (x1 - x0) * (yb - y0) / (y1 - y0)
            t = ((ya + yb) / 2 - y0) / (y1 - y0)
            for col in range(int(min(xa, xb)), int(max(xa, xb)) + 1):
                put(col, row, char, face(t), 1.0, True)
    row = int(b[1] / aspect)
    for col in range(int(round(b[0])), int(round(c[0])) + 1):
        t = (col - b[0]) / max(1e-6, c[0] - b[0])
        put(col, row, "_", mix(PURPLE, PINK, 0.15 + 0.5 * (1 - abs(2 * t - 1))), 1.0, True)
    put(int(a[0]), int(a[1] / aspect), "^", HOT, 1.0, True)

    start = (start_x, top + height * 0.90)
    span = entry[0] - start[0]
    for col in range(int(start[0]), int(entry[0])):
        t = (col + 0.5 - start[0]) / span
        cell = (start[1] + (entry[1] - start[1]) * t) / aspect
        row = int(cell)
        part = cell - row
        char = "¯" if part < 0.3 else "-" if part < 0.7 else "_"
        power = 0.55 + 0.45 * t ** 1.5
        put(col, row, char, mix(DARK, BEAM, power), power, power > 0.8)

    old = dict(cells)
    for row in range(rows):
        for col in range(cols):
            if (col, row) in old:
                continue
            best, colour = 0.0, None
            for dc, dr, weight in ((-1, 0, 1.0), (1, 0, 1.0), (0, -1, 0.7), (0, 1, 0.7)):
                near = old.get((col + dc, row + dr))
                if near and near[2] * weight > best:
                    best, colour = near[2] * weight, near[1]
            if colour is not None and best > 0.3:
                cells[col, row] = (".", mix(DARK, colour, 0.08 + 0.12 * best), 0.0, False)

    lines = []
    for row in range(rows):
        text, previous = "", None
        for col in range(cols):
            if (col, row) not in cells:
                text += " "
                continue
            char, rgb, _power, heavy = cells[col, row]
            if (rgb, heavy) != previous:
                text += "\x1b[%d;38;2;%d;%d;%dm" % ((1 if heavy else 22), *rgb)
                previous = (rgb, heavy)
            text += char
        lines.append(text.rstrip() + "\x1b[0m")
    return lines
