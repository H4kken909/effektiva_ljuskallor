"""Fönstret: öppnar, ritar, väntar och stänger. Räknar inte; den enda modulen i programmet som använder matplotlib."""

import matplotlib.pyplot as plt


def open_plot():
    """Öppnar ett fönster med en tom kurva."""
    plt.ion()
    fig, ax = plt.subplots()
    line = ax.plot([], [])[0]
    return {"fig": fig, "ax": ax, "line": line}


def draw(win, x, values, x_label, y_label):
    """Byter kurvans värden och ritar om."""
    win["line"].set_data(x, values)
    win["ax"].relim()
    win["ax"].autoscale_view()
    win["ax"].set_xlabel(x_label)
    win["ax"].set_ylabel(y_label)
    plt.pause(0.001)


def is_open(win):
    """Sant så länge fönstret inte är stängt."""
    return plt.fignum_exists(win["fig"].number)


def pause(seconds):
    """Låter fönstret rita och ta emot klick en stund."""
    plt.pause(seconds)


def close(win):
    """Stänger fönstret."""
    plt.close(win["fig"])


def show():
    """Visar fönstret tills det stängs."""
    plt.show(block=True)