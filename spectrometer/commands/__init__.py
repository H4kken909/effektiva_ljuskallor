"""Funktionerna i prompten, en rad per kommandomodul. Ta bort en rad, så är den funktionen borta.

Ordningen här är ordningen i help. Namnen är strängar, inte importer, så att ruff inte sorterar om dem.
"""

import importlib

FEATURES = ["basic", "source_cmds", "measure_cmds", "calib_cmds", "correction_cmds", "files_cmds", "session_cmds", "extract_cmds", "profile_cmds", "rig_cmds", "view_cmds", "roi_cmds", "camera_cmds", "series_cmds", "spectra_cmds", "color_cmds", "bandgap_cmds", "accuracy_cmds", "demo_cmds"]


def modules(names=None):
    """Kommandomodulerna i FEATURES-ordning (eller i ordningen names)."""
    return [importlib.import_module(f"{__name__}.{n}") for n in (FEATURES if names is None else names)]
