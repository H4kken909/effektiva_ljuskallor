"""rigg: uppställningens konstruktionsdata (rigg.json) följer med varje mätning i settings.json. Krav 9."""

import json
from pathlib import Path

from spectrometer import out, registry


@registry.command("rigg", "PATH|off: läs uppställningens data ur en JSON-fil, save skriver den (rigg ensam visar den)",
                  "rigg, rigg PATH eller rigg off")
def cmd_rigg(state, args):
    """Kommandot rigg [PATH|off]: läser rigg.json (fälten i docs/rigg.md) till state["rigg"]; save skriver den. DOK-31.

    En ny rigg glömmer mätningen: den mättes med den gamla uppställningen. Tomma fält (null eller "") ger en varning.
    Fel: ValueError med input.invalid_argument om filen inte är giltig JSON eller inte ett objekt {...}; OSError om den
    saknas.
    """
    if not args:
        rig = state["rigg"]
        out.say("rigg: nej" if rig is None else f"rigg: {rig['file']} ({len(rig['fields'])} fält)")
        return
    registry.need(args, ("PATH",), "rigg")
    if args[0] == "off":
        state["rigg"] = None
        state["spectrum"] = None
        out.say("rigg: nej")
        return
    path = Path(args[0])
    try:
        with open(path, encoding="utf-8-sig") as f:  # -sig: en fil från Anteckningar med BOM går också
            fields = json.load(f)
    except json.JSONDecodeError as error:
        raise ValueError(f"input.invalid_argument: {path.name} är inte giltig JSON (rad {error.lineno})") from error
    if not isinstance(fields, dict):
        raise ValueError(f"input.invalid_argument: {path.name} ska vara ett JSON-objekt {{...}} med fälten i docs/rigg.md")
    state["rigg"] = {"file": path.as_posix(), "fields": fields}
    state["spectrum"] = None
    out.say(f"rigg: {path.as_posix()} ({len(fields)} fält)")
    empty = [key for key, value in fields.items() if value is None or value == ""]
    if empty:
        out.warn(f"{len(empty)} fält är tomma: {', '.join(empty)}")
