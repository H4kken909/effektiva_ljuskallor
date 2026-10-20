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


def saturated_count(roi_image, channel):
    """Antalet pixlar i ROI-utsnittet där någon bidragande kanal är mättad, som int."""
    hit = roi_image[:, :, channels(channel)] >= SATURATION
    return int(np.count_nonzero(hit.any(axis=2)))


def saturated_positions(roi_image, axis, channel):
    """Mättnad per position längs spektrumet: bool (P,), sant där någon pixel i remsan tvärs spektrumet är mättad."""
    hit = (roi_image[:, :, channels(channel)] >= SATURATION).any(axis=2)
    return hit.any(axis=0) if axis == "horizontal" else hit.any(axis=1)


def warn_saturated(count):
    """Varnar när count pixlar är mättade; samma text i step, reference och response build."""
    if count:
        out.warn("mättad (255 i råbilden). Sänk exponeringen.")