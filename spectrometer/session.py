"""Sessionen: inställningarna och allt programmet minns mellan två kommandon (ordboken state)."""

from datetime import datetime

from spectrometer import out

DEFAULTS = {
    "source": ("camera", 0),  # ("file", sökväg) eller ("camera", N)
    "roi": None,  # None är hela bilden, annars (x, y, bredd, höjd) i pixlar
    "axis": "horizontal",  # riktningen spektrumet läses längs
    "channel": "gray",  # färgkanal: gray, sum, red, green eller blue
    "output_dir": "data",  # föräldramappen för mätmapparna
    "frames": 1,  # bilder per mätning
    "min_response": 0.01,  # minsta respons, utan enhet
    "min_reference": 1.0,  # minsta referens i counts
}

AXES = ("horizontal", "vertical")


def new_state(settings):
    """Ger en ny state-ordbok med en kopia av inställningarna.

    Parametrar: settings: inställningarna, till exempel DEFAULTS (ändras inte).
    Returnerar: state, en ordbok med nycklarna nedan.
    """
    return {
        "settings": settings.copy(),  # inställningarna, skrivs till settings.json
        "image": None,  # senaste råbilden, (H, W, 3) uint8 i counts, None tills step
        "spectrum": None,  # senaste mätningen (ordbok från measure), None tills step
        "coefficients": None,  # kalibreringens koefficienter, float64, a0 först (calibrate)
        "pixel_range": None,  # kalibreringens giltiga intervall (låg, hög) i pixlar (calibrate)
        "fit_range": None,  # anpassningspunkternas intervall (låg, hög) i pixlar (calibrate)
        "calibration_points_file": None,  # punktfilens sökväg, sha256 (12 tecken) och tid (calibrate)
        "dark": None,  # mörkret, (H, W, 3) float64 i counts (dark)
        "dark_frames": None,  # antal bilder i mörkret (dark), till profiles i settings.json
        "dark_camera": None,  # kamerans reglage när mörkret togs (source.describe), None innan dark
        "response": None,  # responsen: {"x": nm, "values": relativ} (response build)
        "use_response": False,  # True när responsen ska användas (response on och off)
        "reference": None,  # referensspektrumet med kanal, values i counts (reference)
        "mode": "direct",  # "direct" eller "transmission" (mode)
        # bara visningen (theme, view): ändrar aldrig en mätning
        "view": {"theme": "dark", "camera": True, "roi": True, "spectrum": True, "normalize": False,
                 "xlim": None, "ylim": None, "compare": [], "analysis": None},
        "rows": "mean",  # medel eller median över ROI:ns rader (rows); inte i settings, så show är som förut
        "background": None,  # rader på var sida om ROI:n för bakgrunden (background N), None är av
        "taken": {},  # när dark, response, reference och calibrate gjordes (mark_taken), datetime med tidszon
        "rigg": None,  # uppställningens data ur rigg.json: {"file": ..., "fields": {...}} (rigg PATH)
        "controls": {"auto": None, "exposure": None, "gain": None},  # kamerans reglage som du valt; None: drivrutinens
        "series": None,  # mätserien (series start): {"name", "folder", "file"}; None utanför en serie
        "annotations": {},  # current_mA, voltage_V, led, sample, lamp till varje save (series note)
        "note": None,  # fri text till varje save (note)
        "start_settings": None,  # inställningarna när startflaggorna tillämpats (main), det reset går tillbaka till; ej i settings.json
    }


def set_setting(state, key, value):
    """Lägger en inställning i state och glömmer den gamla mätningen.

    roi, channel och axis glömmer också responsen och referensen: de mättes med en annan del av bilden.
    axis glömmer dessutom kalibreringen: den räknar pixlar längs den gamla riktningen.
    """
    state["settings"][key] = value
    state["spectrum"] = None
    if key in ("roi", "channel", "axis"):
        if state["response"] is not None:
            state["response"] = None
            state["use_response"] = False
            out.say("Responsen glömd. Kör response build igen.")
        if state["reference"] is not None:
            state["reference"] = None
            out.say("Referensen glömd. Kör reference igen.")
    if key == "axis" and state["coefficients"] is not None:
        state["coefficients"] = None
        state["pixel_range"] = None
        out.say("Kalibreringen glömd. Kör calibrate igen.")


NOT_UNDONE = ("history", "undo", "image", "spectrum")  # undo lägger aldrig tillbaka dessa


def snapshot(state):
    """En grund kopia av state och en kopia av inställningarna, för undo; utan nycklarna i NOT_UNDONE."""
    copy = {key: value for key, value in state.items() if key not in NOT_UNDONE}
    copy["settings"] = state["settings"].copy()
    return copy


def changed(state, before):
    """True om inställningarna skiljer sig från before, eller om någon annan nyckel pekar på ett annat objekt.

    Kommandona byter objekt (state["dark"] = nytt mörker) i stället för att ändra i dem, så is räcker. image och
    spectrum räknas inte (en ny mätning ångras inte), och visningen (view, theme) ändras på plats och ångras inte.
    """
    if state["settings"] != before["settings"]:
        return True
    keys = (set(state) | set(before)) - set(NOT_UNDONE) - {"settings"}
    return any(state.get(key) is not before.get(key) for key in keys)


def restore(state, before):
    """Lägger tillbaka state från snapshot; historiken, undo-stacken och senaste bilden står kvar, mätningen glöms."""
    kept = {key: state[key] for key in NOT_UNDONE if key in state}
    state.clear()
    state.update(before)
    state.update(kept)
    state["spectrum"] = None


TAKEN_KEYS = {"dark": "dark", "response": "response", "reference": "reference", "calibrate": "coefficients"}
AGE_SHOWN_MIN = 10  # show skriver åldern först från 10 min, så att snabba körningar (facit) ger samma show. PRO-11
DARK_MAX_MIN = 30  # mörker äldre än så ger en varning i step; gränsen bestäms efter driftprovet FYS-17. PRO-12


def mark_taken(state, what, moment=None):
    """Kommer ihåg när what (en nyckel i TAKEN_KEYS) gjordes: nu, eller moment (en datetime med tidszon). PRO-10.

    En ny ordbok i stället för att ändra i den gamla, så att kopian för undo har kvar den gamla tiden.
    """
    state["taken"] = state["taken"] | {what: moment or datetime.now().astimezone()}


def age_minutes(state, what):
    """Hela minuter sedan what gjordes, eller None när det inte finns (aldrig gjort, eller borttaget sedan)."""
    taken = state["taken"].get(what)
    if taken is None or state[TAKEN_KEYS[what]] is None:
        return None
    return int((datetime.now().astimezone() - taken).total_seconds() // 60)


def taken_text(state):
    """Tiden för det som finns, som text (ISO 8601 med tidszon), till "taken" i settings.json. PRO-10."""
    return {what: moment.isoformat(timespec="seconds") for what, moment in state["taken"].items()
            if state[TAKEN_KEYS[what]] is not None}


def warn_old_dark(state):
    """Varning när mörkret är äldre än DARK_MAX_MIN minuter: kamerans temperatur och mörker driver. PRO-12."""
    minutes = age_minutes(state, "dark")
    if minutes is not None and minutes > DARK_MAX_MIN:
        out.warn(f"mörkret är {minutes} min gammalt (gräns {DARK_MAX_MIN}). Kör dark igen.")


def describe(state):
    """Källa, ROI, kanal och mode på en rad: kamera 0 · roi hela bilden · gray · direct."""
    kind, value = state["settings"]["source"]
    roi = state["settings"]["roi"]
    where = "roi hela bilden" if roi is None else "roi " + " ".join(str(v) for v in roi)
    source = f"kamera {value}" if kind == "camera" else f"fil {value}"
    return f"{source} · {where} · {state['settings']['channel']} · {state['mode']}"


def chain(state):
    """Kedjan på en rad: kalibrering och mörker ja/nej, respons nej, på eller av."""
    response = "nej" if state["response"] is None else ("på" if state["use_response"] else "av")
    calibrated = out.YES[state["coefficients"] is not None]
    dark = out.YES[state["dark"] is not None]
    return f"kalibrering {calibrated} · mörker {dark} · respons {response}"


def status_text(state):
    """Statusraden vid prompten: idle, källa, ROI, kanal, mode och kedjan."""
    return f"idle · {describe(state)} · {chain(state)}"


def controls_text(controls):
    """Reglagen som du valt, på en rad: auto off, exposure -6, gain 0 (None hoppas över); tom text om inget är valt."""
    words = []
    for name, value in controls.items():
        if isinstance(value, bool):
            words.append(f"{name} {'on' if value else 'off'}")
        elif value is not None:
            words.append(f"{name} {out.fmt(value)}")
    return ", ".join(words)


def extra_lines(state):
    """Raderna som show skriver sist, bara för det du valt (1.2.x): så är show som förut i facit."""
    lines = []
    controls = controls_text(state["controls"])
    if controls:
        lines.append(f"kamera: {controls}")
    if state["series"] is not None:
        lines.append(f"serie: {state['series']['name']} ({state['series']['file']})")
    if state["annotations"]:
        lines.append(f"series note: {annotations_text(state['annotations'])}")
    if state["note"]:
        lines.append(f"note: {state['note']}")
    return lines


def annotations_text(annotations):
    """series note på en rad: current_mA=20 voltage_V=2.9 led=röd (tal som out.fmt)."""
    return " ".join(f"{key}={out.fmt(value) if isinstance(value, float) else value}" for key, value in annotations.items())
