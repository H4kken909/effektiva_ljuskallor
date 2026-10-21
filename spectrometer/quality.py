"""Mätkvalitet: mättnad i råbilden. Räknar; den enda utskriften är varningen i warn_saturated.

En pixel är mättad när en kanal som bidrar till spektrumet når SATURATION. Kameran kan inte visa mer ljus där,
så värdet blir för lågt och spektrumets form fel (rev7 s.30). Bara bidragande kanaler räknas: red tittar bara
på röd, gray och sum på alla tre.
"""

import numpy as np

from spectrometer import calc, out

SATURATION = 255  # högsta värdet i en 8-bitarsbild; sänk om riggen visar att kameran klipper tidigare (LOG-11)


def crop(image, roi):
    """ROI-utsnittet ur bilden (en vy, ingen kopia), eller hela bilden när roi är None."""
    if roi is None:
        return image
    x, y, width, height = roi
    return image[y:y + height, x:x + width]


def channels(channel):
    """Kanalerna som bidrar till channel, som index i BGR: en för red, green och blue, alla tre för gray och sum."""
    if channel in calc.CHANNEL_INDEX:
        return [calc.CHANNEL_INDEX[channel]]
    return [0, 1, 2]


def _saturated_pixels(roi_image, channel):
    """Mättnad per pixel i ROI-utsnittet: bool (rader, kolumner), sant där någon bidragande kanal är mättad."""
    return (roi_image[:, :, channels(channel)] >= SATURATION).any(axis=2)


def saturated_count(roi_image, channel):
    """Antalet pixlar i ROI-utsnittet där någon bidragande kanal är mättad, som int."""
    return int(np.count_nonzero(_saturated_pixels(roi_image, channel)))


def saturated_positions(roi_image, axis, channel):
    """Mättnad per position längs spektrumet: bool (P,), sant där någon pixel i remsan tvärs spektrumet är mättad."""
    hit = _saturated_pixels(roi_image, channel)
    return hit.any(axis=0) if axis == "horizontal" else hit.any(axis=1)


def warn_saturated(count):
    """Varnar när count pixlar är mättade; samma text i step, reference och response build."""
    if count:
        out.warn("mättad (255 i råbilden). Sänk exponeringen.")


def changed_controls(now, then):
    """Reglagen som skiljer mellan två describe-ordböcker, som [(namn, nu, då)]. None (okänt) jämförs inte."""
    if now is None or then is None:
        return []
    changed = []
    for key, name in (("exposure", "exponeringen"), ("gain", "gain")):
        if now[key] is not None and then[key] is not None and now[key] != then[key]:
            changed.append((name, now[key], then[key]))
    return changed


def warn_changed(now, then, what, command):
    """Varnar för varje reglage som ändrats sedan what (mörkret, referensen) togs, och vilket kommando som hjälper."""
    for name, value, old in changed_controls(now, then):
        out.warn(f"{name} är {value:g} men {what} togs vid {old:g}. Kör {command} igen.")
