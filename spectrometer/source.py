"""Bildkällan: en bildfil eller en webbkamera, lämnad som en ordbok. Filen räknar inte.

Används av main.py. Bilden lämnas som den är, (H, W, 3) uint8 i BGR.
"""

import sys
from pathlib import Path

import cv2
import numpy as np


def open_source(kind, value):
    """Öppnar en bildkälla.

    Parametrar: kind: "file" eller "camera"; value: sökvägen till bildfilen (str eller Path),
    eller kamerans nummer N (int): N i /dev/videoN på Linux, 0 för första kameran på Windows.
    Returnerar: källan som en ordbok: {"kind": "file", "image": (H, W, 3) uint8} eller {"kind": "camera", "cap": VideoCapture}.
    Fel: ValueError med input.invalid_argument för okänd sort; RuntimeError med camera.open_failed om kameran eller
    filen inte går att öppna, filen inte är en bild eller inte har 8 bitar per kanal och formen (H, W, 3).
    """
    if kind == "camera":
        if sys.platform.startswith("linux"):
            backend = cv2.CAP_V4L2  # Video for Linux 2
        elif sys.platform == "win32":
            backend = cv2.CAP_DSHOW  # DirectShow på Windows
        else:
            backend = cv2.CAP_ANY  # OpenCV väljer själv
        message = f"camera.open_failed: kunde inte öppna /dev/video{value}. Kontrollera med v4l2-ctl --list-devices."
        cap = None
        try:
            # Ett nummer som inte ryms i OpenCV:s heltal (till exempel 2147483648) ger cv2.error i stället för False.
            cap = cv2.VideoCapture(value, backend)
            opened = cap.isOpened()
        except cv2.error as error:
            if cap is not None:
                cap.release()
            raise RuntimeError(message) from error
        if not opened:
            cap.release()
            raise RuntimeError(message)
        return {"kind": "camera", "cap": cap}
    if kind != "file":
        raise ValueError(f"input.invalid_argument: Type is unknown {kind}")
    if not Path(value).is_file():
        raise RuntimeError(f"camera.open_failed: Image source does not exist {value}")
    data = np.fromfile(value, np.uint8)  # imdecode i stället för imread: klarar åäö i Windows-sökvägar
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED) if data.size else None
    if img is None:
        raise RuntimeError(f"camera.open_failed: Could not open {value} as image")
    if img.dtype != "uint8":
        raise RuntimeError(f"camera.open_failed: Non-8bit per channel, {img.dtype}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.ndim == 3 and img.shape[-1] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    if img.ndim != 3 or img.shape[-1] != 3:
        raise RuntimeError(
            f"camera.open_failed: Image is not (H, W, 3), shape is {img.shape}"
        )
    return {"kind": kind, "image": img}


def read_frame(src):
    """Ger en bild ur källan: en ny bild från kameran, eller en kopia av filens bild.

    Parametrar: src: ordboken från open_source.
    Returnerar: bilden, (H, W, 3) uint8 i BGR och counts.
    Fel: RuntimeError med camera.read_failed om kameran inte ger någon bild.
    """
    if src["kind"] == "camera":
        ok, image = src["cap"].read()
        if not ok or image is None:
            raise RuntimeError(
                "camera.read_failed: kunde inte läsa en bild från kameran"
            )
        return image
    if src["kind"] == "file":
        return src["image"].copy()


def close_source(src):
    """Stänger källan: släpper kameran; en fil behöver inte stängas.

    Parametrar: src: ordboken från open_source.
    Returnerar: None
    Fel: inga.
    """
    if src["kind"] == "camera":
        src["cap"].release()
