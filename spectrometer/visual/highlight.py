import re

WORDS = {}
for tag, words in (
    ("name", "exposure gain roi frames channel mode source dark calibration response reference cal auto rows "
             "background axis glow"),
    ("ok", "ok done saved yes on valid ready installed found written wrote ✓ ●"),
    ("warn", "warning paused slow missing skipped hint"),
    ("bad", "error stale failed cannot unexpected lost"),
):
    for word in words.split():
        WORDS[word] = tag

UNIT = re.compile(r"\s?(?:frames|draws|measurements)/s|\s?(?:nm|ms|counts|px|fps|MB|KB|s)(?![\w])|\s?%|/s(?![\w])")

TOKEN = re.compile(
    r"(?P<path>"
    r"(?<![\w.])[A-Za-z]:[\\/][^\s,;\"'()]*"
    r"|(?<!\S)(?:~|\.{1,2})?/(?:[\w.\-]+/?)+"
    r"|(?<![\w./])[A-Za-z_][\w\-]*(?:/[\w.\-]+)*/[\w.\-]*\d[\w.\-]*/?"
    r"|(?<![\w./])(?:[\w\-]+/)*[\w\-]+\.(?:csv|png|jpe?g|json|txt|xlsx|log|md|bmp|tiff?|ansi|desktop|lnk|py)(?!\w)"
    r")"
    r"|(?P<wave>(?<![\w.])\d+(?:\.\d+)?(?=\s?nm(?!\w)))"
    r"|(?P<num>(?<![\w.#])[-+]?\d+(?:\.\d+)*(?:e[-+]?\d+)?(?![\w]))"
    r"|(?P<word>[A-Za-z][A-Za-z_]*|[✓●▲])"
)


def segments(text, kind=None):
    whole = {"warn": "warn", "error": "bad"}.get(kind)
    found = []
    for match in TOKEN.finditer(text):
        group = match.lastgroup
        start, end = match.span()
        if group == "path":
            found.append((start, end, "path"))
        elif whole is not None:
            continue
        elif group in ("wave", "num"):
            found.append((start, end, group))
            unit = UNIT.match(text, end)
            if unit and unit.group().strip():
                found.append((unit.start() + (unit.group()[0] == " "), unit.end(), "unit"))
        elif match.group().lower() in WORDS:
            found.append((start, end, WORDS[match.group().lower()]))
        elif match.group() == "▲":
            found.append((start, end, "bad" if kind == "stale" else "warn"))
    found.sort(key=lambda piece: (piece[0], -piece[1]))
    end = len(text.rstrip("\n")) if whole else len(text)
    parts, at = [], 0
    for start, stop, tag in [*found, (end, end, None)]:
        if start < at:
            continue
        if start > at:
            parts.append((text[at:start], whole))
        if stop > start:
            parts.append((text[start:stop], tag))
        at = stop
    if at < len(text):
        parts.append((text[at:], None))
    return parts
