from datetime import datetime

from spectrometer.core import out

DEFAULTS = {
    "source": ("camera", 0),
    "roi": None,
    "axis": "horizontal",
    "channel": "gray",
    "output_dir": "data",
    "frames": 1,
}


def new_state(settings):
    return {
        "settings": settings.copy(),
        "image": None,
        "spectrum": None,
        "coefficients": None,
        "pixel_range": None,
        "fit_range": None,
        "calibration_points_file": None,
        "dark": None,
        "dark_camera": None,
        "response": None,
        "use_response": False,
        "reference": None,
        "mode": "direct",
        "view": {"camera": True, "roi": True, "spectrum": True, "panel": False, "normalize": False,
                 "glow": "on", "rail": True, "status": True, "camera_view": "crop"},
        "taken": {},
        "controls": {"auto": None, "exposure": None, "gain": None},
        "series": None,
        "annotations": {},
        "note": None,
    }


def forget_response(state):
    if state["response"] is not None:
        state["response"] = None
        state["use_response"] = False
        out.say("Response forgotten. Run response build again.")


def forget_reference(state):
    if state["reference"] is not None:
        state["reference"] = None
        out.say("Reference forgotten. Run reference again.")
        if state["mode"] == "transmission":
            state["mode"] = "direct"
            out.say("mode: direct (no reference)")


def set_setting(state, key, value):
    if state["settings"][key] == value:
        return
    state["settings"][key] = value
    state["spectrum"] = None
    if key in ("roi", "channel", "axis"):
        forget_response(state)
        forget_reference(state)
    if key == "axis" and state["coefficients"] is not None:
        state["coefficients"] = None
        state["pixel_range"] = None
        out.say("Calibration forgotten. Run calibrate again.")


TAKEN_KEYS = {"dark": "dark", "response": "response", "reference": "reference", "calibrate": "coefficients"}


def mark_taken(state, what):
    state["taken"][what] = datetime.now().astimezone()


def age_minutes(state, what):
    taken = state["taken"].get(what)
    if taken is None or state[TAKEN_KEYS[what]] is None:
        return None
    return int((datetime.now().astimezone() - taken).total_seconds() // 60)


def describe(state):
    kind, value = state["settings"]["source"]
    roi = state["settings"]["roi"]
    where = "roi full image" if roi is None else "roi " + " ".join(str(v) for v in roi)
    return f"{kind} {value} · {where} · {state['settings']['channel']} · {state['mode']}"


def chain(state):
    response = "no" if state["response"] is None else "on" if state["use_response"] else "off"
    return (f"calibration {out.YES[state['coefficients'] is not None]} · dark {out.YES[state['dark'] is not None]}"
            f" · response {response}")
