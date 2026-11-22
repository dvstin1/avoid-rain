"""
Pytest configuration and shared fixtures.
Isolates unit/integration test NetworkManager ports from the live game's LAN_PORT (55555)
and guarantees all test NetworkManager background sockets are closed on test teardown.
"""

import pytest

import constants
import engine.network_manager
import engine.stats
from engine.network_manager import NetworkManager


@pytest.fixture(autouse=True)
def _isolate_default_save_path(monkeypatch, tmp_path):
    """Redirect engine.stats.DEFAULT_PATH to an isolated tmp_path so pytest never clobbers live save_data.json."""
    monkeypatch.setattr(engine.stats, "DEFAULT_PATH", tmp_path / "save_data.json")


@pytest.fixture(autouse=True)
def _isolate_test_lan_ports(monkeypatch):
    """Redirect default LAN_PORT to TEST_LAN_PORT_BASE (51000) and clean up sockets after each test."""
    monkeypatch.setattr(constants, "LAN_PORT", constants.TEST_LAN_PORT_BASE)
    monkeypatch.setattr(engine.network_manager, "LAN_PORT", constants.TEST_LAN_PORT_BASE)

    created_managers = []
    orig_init = NetworkManager.__init__

    def _tracked_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        created_managers.append(self)

    monkeypatch.setattr(NetworkManager, "__init__", _tracked_init)
    yield
    for nm in created_managers:
        try:
            nm.stop_network()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
