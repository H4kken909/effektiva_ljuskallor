"""Coordinates the program. Run with python -m spectrometer.main and imagesource"""

import argparse
import sys
import matplotlib.pyplot as plt
import numpy as np

from spectrometer import calc, files, plot, source

def main():
    parser = argparse.ArgumentParser(prog="python -m spectrometer.main", description="Läser en bildfil, skriver toppen, sparar mätningen och ritar spektrumet.")
    parser.add_argument("path", help="sökvägen till en bildfil")
    args = parser.parse_args()

    state = new_state(DEFAULTS)
    state["settings"]["source"] = ("file", args.path)

    try:
        spectrum = measure(state)
        i = np.argmax(spectrum["values"])
        print(f"Topp {spectrum["values"][i]:g} vid pixel {spectrum["x"][i]:g}")

        folder = files.save_measurement(state["settings"]["output_dir"], spectrum, state["image"], state["settings"])
        print(f"Sparad i {folder.as_posix()}")

        win = plot.open_plot()
        plot.draw(win, spectrum["x"], np.where(spectrum["mask"], spectrum["values"], np.nan), spectrum["x_label"], spectrum["y_label"])
        plt.show(block=True)

    except (ValueError, RuntimeError, OSError) as err:
        print(f"Fel: {err}")
        return 1
    return 0


DEFAULTS = {
    "source": ("camera", 0), # ("file", sökväg eller "camera", N)
    "roi": None, # None är hela bilden, annars (x, y, bredd, höjd) i pixlar
    "axis": "horizontal", # riktningen spektrumet läses längs
    "channel": "gray", # färgkanal: gray, sum, red, green eller blue
    "output_dir": "data", # föräldramappen för mätmapparna
    "frames": 1, "bilder per mätning"
    "min_response": 0.01, # minsta respons, utan enhet
    "min:reference": 1.0, # minsta referens i counts
}

def new_state(settings):
    return {"settings": settings.copy(), "image": None, "spectrum": None}

def measure(state):
    cfg = state["settings"]
    kind, value = cfg["source"]

    handle = source.open_source(kind, value)
    try:
        image = source.read_frame(handle)
    finally:
        source.close_source(handle)
    roi = cfg["roi"]

    if cfg["roi"] is None:
        roi = (0, 0, image.shape[1], image.shape[0])

    table = calc.prepare(image, roi, cfg["axis"], cfg["channel"])
    values = calc.extract_spectrum(table)

    if cfg["axis"] == "horizontal":
        first, count = roi[0], roi[2]
    else:
        first, count = roi[1], roi[3]
    x = np.arange(first, first + count).astype("float64")
    mask = np.isfinite(values)

    spectrum = {"x": x, "values": values, "mask": mask, "x_label": "pixel", "y_label": "signal (counts)"}
    state["image"] = image
    state["spectrum"] = spectrum
    return spectrum

if __name__ == "__main__":
    sys.exit(main())