import sys
import time

import cv2
import numpy as np


def open_source(kind, value):
    if kind == "file":
        data = np.fromfile(value, np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
        if image is None:
            raise RuntimeError(f"Could not open {value} as image")
        return {"kind": "file", "image": image}
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY] if sys.platform == "win32" else [cv2.CAP_V4L2]
    for backend in backends:
        try:
            cap = cv2.VideoCapture(value, backend)
        except cv2.error:
            continue
        if cap.isOpened():
            return {"kind": "camera", "cap": cap}
        cap.release()
    raise RuntimeError(f"could not open camera {value}. Close other programs that use it or try another number.")


def read_frame(src):
    if src["kind"] == "file":
        return src["image"].copy()
    for attempt in range(3):
        if attempt > 0:
            time.sleep(0.05)
        try:
            ok, image = src["cap"].read()
        except cv2.error:
            ok = False
        if ok:
            return image
    raise RuntimeError("could not read an image from the camera")


def close_source(src):
    if src["kind"] == "camera":
        src["cap"].release()


CONTROLS = {"exposure": cv2.CAP_PROP_EXPOSURE, "gain": cv2.CAP_PROP_GAIN, "auto": cv2.CAP_PROP_AUTO_EXPOSURE}
PROPS = {"width": cv2.CAP_PROP_FRAME_WIDTH, "height": cv2.CAP_PROP_FRAME_HEIGHT, "exposure": cv2.CAP_PROP_EXPOSURE,
         "gain": cv2.CAP_PROP_GAIN, "auto_exposure": cv2.CAP_PROP_AUTO_EXPOSURE, "fps": cv2.CAP_PROP_FPS}


def describe(src):
    info = {"kind": src["kind"], "backend": None, "fourcc": None, **dict.fromkeys(PROPS)}
    if src["kind"] != "camera":
        return info
    cap = src["cap"]
    info["backend"] = cap.getBackendName()
    code = int(cap.get(cv2.CAP_PROP_FOURCC))
    if code > 0:
        info["fourcc"] = "".join(chr((code >> 8 * i) & 0xFF) for i in range(4))
    for key, prop in PROPS.items():
        info[key] = cap.get(prop)
    return info


def auto_values(backend):
    return (1.0, 3.0) if backend == "V4L2" else (0.25, 0.75)


def set_control(src, name, value):
    if src["kind"] != "camera":
        return True
    if name == "auto":
        value = auto_values(describe(src)["backend"])[1 if value else 0]
    return bool(src["cap"].set(CONTROLS[name], float(value)))


def auto_on(camera):
    return camera.get("auto_exposure") == auto_values(camera["backend"])[1]


TONE = np.clip(np.rint(255 * np.clip(np.arange(256) * 1.35 / 255, 0, 1) ** 0.8), 0, 255).astype(np.uint8)
_SHINE = np.rint(255 * np.clip((np.arange(256) / 255 - 0.55) / (1 - 0.55), 0, 1)).astype(np.uint8)


def bloom(rgb):
    toned = cv2.LUT(np.ascontiguousarray(rgb), TONE)
    shine = _SHINE[np.maximum(np.maximum(toned[..., 0], toned[..., 1]), toned[..., 2])]
    light = cv2.multiply(toned, cv2.merge((shine, shine, shine)), scale=1 / 255)
    halo = cv2.convertScaleAbs(cv2.GaussianBlur(light, (0, 0), 3.0), alpha=0.45)
    return cv2.bitwise_not(cv2.multiply(cv2.bitwise_not(toned), cv2.bitwise_not(halo), scale=1 / 255))
