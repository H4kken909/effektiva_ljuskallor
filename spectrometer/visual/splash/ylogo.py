import math


def render(rows, aspect=2.1):
    rows = max(1, rows)
    kx = max(1, round(rows * aspect * 502 / 531)) / 502
    k = max(4, round(167 * kx))
    step = max(1, round(335 * kx / rows))
    n = max(2, min(rows - 2, round(2 * 102 / 531 * rows)))
    w = max(4, 2 * round((n - 0.3) * aspect / 2))
    circle = []
    for i in range(n):
        dy = abs(2 * i - n + 1) / n
        inset = 0 if n <= 3 else round(w / 2 * (1 - math.sqrt(max(0.0, 1 - dy * dy))))
        inner = w - 2 * inset
        if 2 * i < n - 1:
            text = "d" + "8" * (inner - 2) + "b"
        elif 2 * i > n - 1:
            text = "Y" + "8" * (inner - 2) + "P"
        else:
            text = "8" * inner
        circle.append(" " * inset + text)
    x0 = max(0, max(len(text) + 2 - step * (rows - 1 - i) for i, text in enumerate(circle)))
    circle += [""] * (rows - n)
    bar = [" " * (x0 + step * (rows - 1 - r)) + "d" + "8" * (k - 2) + "P" for r in range(rows)]
    used = max(len(line.rstrip()) for line in circle + bar)
    lines = []
    for c, b in zip(circle, bar):
        c = c.ljust(used)[:used]
        b = b.ljust(used)[:used]
        lines.append("".join(b[i] if b[i] != " " else c[i] for i in range(used)))
    return lines


def width(rows, aspect):
    return len(render(rows, aspect)[0])
