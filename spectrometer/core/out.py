import sys

YES = {True: "yes", False: "no"}
sink = None


def tty(stream):
    return stream is not None and stream.isatty()


def set_sink(window):
    global sink
    sink = window


def interactive():
    return sink is not None or tty(sys.stdin)


def say(text="", style=None):
    if sink is not None:
        sink.write(f"{text}\n", style)
    else:
        print(text)


def error(text):
    say(f"Error: {text}", "error")


def warn(text):
    say(f"Warning: {text}", "warn")


def ask(prompt):
    if sink is not None:
        return sink.ask(prompt)
    return input(prompt)


def fmt(x):
    return f"{x:g}"


def table(rows):
    for left, right in rows:
        if sink is not None:
            sink.write(f"{left} {right}\n", ("table", len(str(left))))
        else:
            print(f"{left} {right}")


def pm(value, uncertainty, unit=""):
    tail = f" {unit}" if unit else ""
    if not (0 < uncertainty < float("inf") and abs(value) < float("inf")):
        return f"{fmt(value)}{tail}"
    mantissa, exponent = f"{uncertainty:e}".split("e")
    decimals = (2 if mantissa[0] in "12" else 1) - 1 - int(exponent)
    if decimals > 0:
        return f"{value:.{decimals}f} ± {uncertainty:.{decimals}f}{tail}"
    return f"{round(value, decimals):.0f} ± {round(uncertainty, decimals):.0f}{tail}"
