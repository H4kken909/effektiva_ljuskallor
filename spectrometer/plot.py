"""Creates the window, does not compute"""

import matplotlib.pyplot as plt


def open_plot():
    """Opens window with empty curve"""

    plt.ion()
    fig, ax = plt.subplots()

    lines = ax.plot([], [])
    line = lines[0]

    return {"fig": fig, "ax": ax, "line": line}

def draw(win, x, values, x_label, y_label):
    """Changes the values of the curve and redraws"""
    
    win["line"].set_data(x, values)
    win["ax"].relim()
    win["ax"].autoscale_view()
    win["ax"].set_xlabel(x_label)
    win["ax"].set_ylabel(y_label)

    plt.pause(0.001)