import pytest

from spectrometer import commands
from spectrometer.core import registry


@pytest.fixture(autouse=True)
def load_commands():
    registry.load(commands.modules())


@pytest.fixture(autouse=True)
def own_settings_folder(monkeypatch, tmp_path_factory):
    monkeypatch.setenv("SPEKTRO_CONFIG", str(tmp_path_factory.mktemp("settings")))


@pytest.fixture(autouse=True)
def terminal_only(monkeypatch):
    monkeypatch.setenv("SPEKTRO_TERMINAL", "1")
