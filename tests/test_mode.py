"""Demo mode blocks uploads; live mode is set up on purpose (config.APP_MODE).

The block is in the backend, not only the screens: a firm's documents must not
reach a demo even when someone calls the API directly.
"""

import importlib

from fastapi.testclient import TestClient

import config
from app import app

client = TestClient(app)
_PDF = ("files", ("doc.pdf", b"%PDF-1.4 not really", "application/pdf"))


def test_demo_mode_refuses_uploads(monkeypatch):
    monkeypatch.setattr("config.APP_MODE", "demo")
    response = client.post("/api/batch", files=[_PDF])

    assert response.status_code == 403
    assert "demo mode" in response.json()["detail"]


def test_live_mode_accepts_uploads(monkeypatch):
    monkeypatch.setattr("config.APP_MODE", "live")

    assert client.post("/api/batch", files=[_PDF]).status_code == 200


def test_the_page_can_ask_which_mode(monkeypatch):
    monkeypatch.setattr("config.APP_MODE", "demo")

    assert client.get("/api/mode").json() == {"mode": "demo"}


def test_no_setting_means_demo(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)

    assert importlib.reload(config).APP_MODE == "demo"


def test_only_the_exact_word_live_switches_it_on(monkeypatch):
    """A typo stays safe."""
    for value, expected in [("live", "live"), (" LIVE ", "live"), ("liv", "demo"), ("yes", "demo")]:
        monkeypatch.setenv("APP_MODE", value)
        assert importlib.reload(config).APP_MODE == expected
    monkeypatch.delenv("APP_MODE")
    importlib.reload(config)
