"""Source, does not compute"""

from pathlib import Path

import cv2

def open_source(kind, value):
    """
    Opens source and reads image

    Parameters:
        kind: The kind, "file" (str).
        value: Searchpath to imagesource (str or Path).
    Returns:
        dictionairy with "kind" and "image", image (H, W, 3) uint8 in BR (dict).
    Errors
        ValueError with input.invalid_argument if type is unknown
        RuntimeError with copemar.open_failed if file is missing or is not an image or does not have 8 bits per channel.
    """

    if kind != "file":
        raise ValueError(f"input.invalid_argument: Type is unknown {kind}")

    if not Path(value).is_file():
        raise RuntimeError(f"camera.open_failed: Image source does not exist {value}")

    img = cv2.imread(str(value), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(f"camera.open_failed: Could not open {img} as image")

    if img.dtype != "uint8":
        raise RuntimeError(f"camera.open_failed: Non-8bit per channel, {img.dtype}")

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[-1] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    if img.ndim != 3 or img.shape[-1] != 3:
        raise RuntimeError(f"camera.open_failed: Image is not {img.shape}")
    return {"kind": kind, "image": img}

def read_frame(src):
    """Reads frame"""
    if src["kind"] == "file":
        return src["image"].copy()

def close_source(src):
    """Stänger källan"""

"""


"""