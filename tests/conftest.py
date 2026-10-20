"""Gemensamt för testerna: kommandoregistret laddas före varje test, som när programmet startar."""

import pytest

from spectrometer import commands, registry


@pytest.fixture(autouse=True)
def kommandon():
    """Alla kommandon i registret."""
    registry.load(commands.modules())