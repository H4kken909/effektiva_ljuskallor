"""Sessionen: inställningarna och allt programmet minns mellan två kommandon (ordboken state)."""

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
        "dark": None,  # mörkret, (H, W, 3) float64 i counts (dark)
        "response": None,  # responsen: {"x": nm, "values": relativ} (response build)
        "use_response": False,  # True när responsen ska användas (response on och off)
        "reference": None,  # referensspektrumet med kanal, values i counts (reference)
        "mode": "direct",  # "direct" eller "transmission" (mode)
    }


def set_setting(state, key, value):
    """Lägger en inställning i state och glömmer den gamla mätningen (roi och channel glömmer också responsen)."""
    state["settings"][key] = value
    state["spectrum"] = None
    if key in ("roi", "channel") and state["response"] is not None:
        state["response"] = None
        state["use_response"] = False
        out.say("Responsen glömd. Kör response build igen.")