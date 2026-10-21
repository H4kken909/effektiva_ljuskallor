"""Bildkällan: en bildfil eller en webbkamera, lämnad som en ordbok. Filen räknar inte.

Används av main.py. Bilden lämnas som den är, (H, W, 3) uint8 i BGR.
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

READ_TRIES = 3  # försök per bild innan camera.read_failed; ett enstaka tappat read() ska inte stoppa live
READ_PAUSE = 0.05  # sekunder mellan försöken
WARMUP_FRAMES = 0  # bilder som läses och kastas direkt efter att kameran öppnats; 0 tills uppvärmningen är mätt
MAX_MPIXEL = 40  # största bildfil i miljoner pixlar; float64 × 3 kanaler är 24 byte per pixel


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
            backends = [cv2.CAP_V4L2]  # Video for Linux 2
            message = f"camera.open_failed: kunde inte öppna /dev/video{value}. Kontrollera med v4l2-ctl --list-devices."
        elif sys.platform == "win32":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]  # DirectShow, Media Foundation, sist OpenCV:s val
            message = (f"camera.open_failed: kunde inte öppna kamera {value}. Stäng program som kan använda den "
                       "(Kamera-appen, Teams, webbläsaren), se efter att appar får använda kameran "
                       f"(Inställningar > Sekretess > Kamera) eller prova source camera {value + 1}.")
        else:
            backends = [cv2.CAP_ANY]  # OpenCV väljer själv
            message = f"camera.open_failed: kunde inte öppna kamera {value}. Prova ett annat nummer."
        error = None
        for backend in backends:
            cap = None
            try:
                # Ett nummer som inte ryms i OpenCV:s heltal (till exempel 2147483648) ger cv2.error i stället för False.
                cap = cv2.VideoCapture(value, backend)
                if cap.isOpened():
                    return warm_up({"kind": "camera", "cap": cap})
            except cv2.error as err:
                error = err
            except RuntimeError as err:  # öppnades men gav ingen bild (warm_up har släppt den): prova nästa backend
                message = str(err)
                error = err
            if cap is not None:
                cap.release()
        raise RuntimeError(message) from error
    if kind != "file":
        raise ValueError(f"input.invalid_argument: Type is unknown {kind}")
    if Path(value).is_dir():
        return open_folder(value)
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
        raise RuntimeError(f"camera.open_failed: Image is not (H, W, 3), shape is {img.shape}")
    if img.shape[0] * img.shape[1] > MAX_MPIXEL * 1e6:
        raise ValueError(f"input.invalid_argument: bilden är {img.shape[0] * img.shape[1] / 1e6:.3g} Mpixel, högst {MAX_MPIXEL:g}")
    return {"kind": kind, "image": img}


def read_frame(src):
    """Ger en bild ur källan: en ny bild från kameran, eller en kopia av filens bild.

    Parametrar: src: ordboken från open_source.
    Returnerar: bilden, (H, W, 3) uint8 i BGR och counts.
    Fel: RuntimeError med camera.read_failed om kameran inte ger någon bild.
    """
    if src["kind"] == "camera":
        error = None
        for attempt in range(READ_TRIES):
            if attempt:
                time.sleep(READ_PAUSE)
            try:
                ok, image = src["cap"].read()
            except cv2.error as err:  # en trasig bild från drivrutinen
                ok, image, error = False, None, err
            if ok and image is not None:
                return image
        raise RuntimeError("camera.read_failed: kunde inte läsa en bild från kameran") from error
    if src["kind"] == "file":
        return src["image"].copy()
    if src["kind"] == "folder":
        return next_in_folder(src)


def close_source(src):
    """Stänger källan: släpper kameran; en fil behöver inte stängas.

    Parametrar: src: ordboken från open_source.
    Returnerar: None
    Fel: inga.
    """
    if src["kind"] == "camera":
        src["cap"].release()


def warm_up(src):
    """Läser och kastar WARMUP_FRAMES bilder direkt efter att kameran öppnats (de första kan vara mörkare).

    Returnerar: src. Fel: RuntimeError med camera.open_failed, och kameran släppt, om den inte ger någon bild
    (open_source fångar felet och provar nästa backend).
    """
    for _ in range(WARMUP_FRAMES):
        try:
            read_frame(src)
        except RuntimeError as error:
            close_source(src)
            raise RuntimeError("camera.open_failed: kameran öppnades men ger ingen bild; prova nästa nummer") from error
    return src


def read_frames(src, n):
    """n bilder i rad ur en öppen källa, som en lista. Fel: som read_frame."""
    return [read_frame(src) for _ in range(n)]


def describe(src):
    """Vad källan och drivrutinen säger om sig själva, som en ordbok; ingen utskrift.

    Nycklar: kind, backend, fourcc, width, height, exposure, gain, auto_exposure, fps. För en bildfil är allt utom
    kind None. Kamerans tal är drivrutinens egna, utan enhet (antaget: V4L2 och DirectShow räknar exponeringen
    olika), och 0 eller -1 kan betyda att reglaget saknas. De duger för att se om något ändrats, inte mer.
    """
    info = {"kind": src["kind"], "backend": None, "fourcc": None, "width": None, "height": None,
            "exposure": None, "gain": None, "auto_exposure": None, "fps": None}
    if src["kind"] != "camera":
        return info
    cap = src["cap"]
    if not hasattr(cap, "get"):  # en drivrutin (eller ett låtsasobjekt i ett test) utan reglage: bara kind
        return info
    info["backend"] = cap.getBackendName() if hasattr(cap, "getBackendName") else None
    code = int(cap.get(cv2.CAP_PROP_FOURCC))  # fyra tecken i ett heltal, första tecknet i lägsta byten
    info["fourcc"] = "".join(chr((code >> 8 * i) & 0xFF) for i in range(4)) if code > 0 else None
    props = {"width": cv2.CAP_PROP_FRAME_WIDTH, "height": cv2.CAP_PROP_FRAME_HEIGHT, "exposure": cv2.CAP_PROP_EXPOSURE,
             "gain": cv2.CAP_PROP_GAIN, "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE, "fps": cv2.CAP_PROP_FPS}
    for key, prop in props.items():
        info[key] = cap.get(prop)
    return info


def probe(max_index=4):
    """Provar kamera 0 till max_index: öppnar, läser en bild och stänger. Ger [(index, bredd, höjd)] för dem som ger bild."""
    found = []
    for index in range(max_index + 1):
        try:
            src = open_source("camera", index)
        except RuntimeError:
            continue  # ingen kamera med det numret
        try:
            image = read_frame(src)
        except RuntimeError:
            continue  # öppnades men gav ingen bild
        finally:
            close_source(src)
        found.append((index, image.shape[1], image.shape[0]))
    return found


def open_folder(folder):
    """En mapp med bilder som källa: sorterade *.png och *.jpg, en bild per read_frame (döp dem 001.png, 002.png ...).

    Fel: RuntimeError med camera.open_failed om mappen inte har några png- eller jpg-bilder.
    """
    paths = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not paths:
        raise RuntimeError(f"camera.open_failed: inga png- eller jpg-bilder i mappen {folder}")
    return {"kind": "folder", "paths": paths, "next": 0}


def next_in_folder(src):
    """Nästa bild i mappen, kontrollerad som en bildfil. Fel: RuntimeError med camera.read_failed när bilderna är slut."""
    if src["next"] >= len(src["paths"]):
        raise RuntimeError(f"camera.read_failed: slut på bilderna i mappen ({len(src['paths'])} st)")
    path = src["paths"][src["next"]]
    src["next"] += 1
    return open_source("file", path)["image"]


CONTROLS = {"exposure": cv2.CAP_PROP_EXPOSURE, "gain": cv2.CAP_PROP_GAIN, "auto": cv2.CAP_PROP_AUTO_EXPOSURE}
AUTO_VALUES = {"V4L2": (1.0, 3.0)}  # CAP_PROP_AUTO_EXPOSURE som (manuell, auto); V4L2 räknar 1 och 3
AUTO_OTHER = (0.25, 0.75)  # DirectShow och övriga: OpenCV:s gamla skala (antaget, prova med info vid riggen)


def set_control(src, name, value):
    """Sätter ett reglage i en öppen kamera: exposure och gain med drivrutinens tal, auto med True eller False.

    En bildfil (eller en kamera utan reglage) har inget att sätta. Returnerar: False om drivrutinen sa nej, annars True.
    """
    cap = src.get("cap")
    if src["kind"] != "camera" or not hasattr(cap, "set"):
        return True
    if name == "auto":
        manual, auto = AUTO_VALUES.get(describe(src)["backend"], AUTO_OTHER)
        value = auto if value else manual
    return bool(cap.set(CONTROLS[name], float(value)))


def get_controls(src):
    """exposure, gain och auto (True, False eller None om det inte går att se) som drivrutinen säger nu."""
    info = describe(src)
    return {"exposure": info["exposure"], "gain": info["gain"], "auto": auto_on(info)}


def auto_on(camera):
    """Sant om drivrutinen säger auto-exponering, falskt vid manuell, None annars (camera: ordboken från describe)."""
    if camera.get("auto_exposure") is None:
        return None
    manual, auto = AUTO_VALUES.get(camera["backend"], AUTO_OTHER)
    return {manual: False, auto: True}.get(camera["auto_exposure"])
