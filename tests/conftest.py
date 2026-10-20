"""Gemensamt för testerna: kommandoregistret laddas före varje test, som när programmet startar."""

import pytest

from spectrometer import commands, registry


@pytest.fixture(autouse=True)
def kommandon():
    """Alla kommandon i registret."""
    registry.load(commands.modules())


@pytest.fixture(autouse=True)
def utan_farg(monkeypatch):
    """Ingen färg i testerna, inte ens med pytest -s i en terminal: utskriften jämförs tecken för tecken."""
    from spectrometer import out

    monkeypatch.setattr(out, "FARG", False)
