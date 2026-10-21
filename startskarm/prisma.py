"""Pink Floyd prism: colour style, no dependencies."""

# Koordinater i en ritning där x går från 0 till 640 och y från 20 till 340.
A, B, C = (319, 68), (218, 241), (415, 241)  # prismats hörn: topp, nere till vänster, nere till höger
ENTRY = (273, 147)  # där den vita strålen går in i prismat
TOP, BOTTOM = (355, 131), (375, 169)  # där ljuset går ut på andra sidan
COLORS = [(255, 62, 40), (255, 144, 30), (255, 235, 65),
          (110, 235, 80), (70, 195, 255), (190, 135, 255)]  # regnbågens sex band
GLASS = (210, 230, 240)  # prismats linjer och inre
BEAM = (255, 252, 229)  # den vita strålen in


def inside(x, y, vertices):
    """Ligger (x, y) i polygonen? Sant när punkten är på samma sida av alla kanter."""
    signs = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        signs.append((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]))
    return min(signs) >= 0 or max(signs) <= 0


def render(style, width, height):
    """Prismat som en lista rader med färgkoder (style används inte)."""
    return geometric(width, height)


def geometric(width, height):
    """Rita prismat på ett rutnät width x height och ge raderna som text med ANSI-färger."""
    canvas = [[' '] * width for _ in range(height)]
    colors = [[GLASS] * width for _ in range(height)]

    def plot(x, y, char, rgb=GLASS):
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x], colors[y][x] = char, rgb

    def point(p):
        """Ritningens punkt omräknad till en ruta i rutnätet."""
        return round(p[0] / 640 * (width - 1)), round((p[1] - 20) / 320 * (height - 1))

    def stroke(a, b, char, rgb=GLASS):
        """Dra en rak linje av tecknet char från a till b."""
        x0, y0 = point(a)
        x1, y1 = point(b)
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            plot(round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps), char, rgb)

    # Fyll i prismats inre och den uppspridda strålen, ruta för ruta
    for row in range(height):
        for col in range(width):
            x, y = col * 640 / (width - 1), row * 320 / (height - 1) + 20
            if inside(x, y, [ENTRY, TOP, BOTTOM]):
                plot(col, row, '.' if x < 325 else ':')
            if inside(x, y, [TOP, (640, 180), (640, 240), BOTTOM]):
                # Strålens övre och undre kant är räta linjer från TOP och BOTTOM till x = 640 (y 180 och 240)
                upper = 131 + (x - 355) * 49 / 285
                lower = 169 + (x - 375) * 71 / 265
                band = max(0, min(5, int((y - upper) / (lower - upper) * 6)))
                plot(col, row, ':=+*#@'[band], COLORS[band])

    stroke(A, B, '/')
    stroke(A, C, '\\')
    stroke(B, C, '_')
    stroke((0, 215), ENTRY, '-', BEAM)
    ax, ay = point(A)
    plot(ax, ay, '^')

    # Bygg raderna; en färgkod bara när färgen byter
    output = []
    for chars, rgbs in zip(canvas, colors):
        parts = []
        previous = None
        for char, rgb in zip(chars, rgbs):
            if char != ' ' and rgb != previous:
                parts.append('\x1b[38;2;%d;%d;%dm' % rgb)
                previous = rgb
            parts.append(char)
        output.append(''.join(parts).rstrip() + '\x1b[0m')
    return output
