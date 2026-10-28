"""One address for the tool: the React page at /.

There is no demo mode: /api/batch always reads what it is sent, because the
tool only ever runs on the computer whose documents it reads.
"""

from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


def test_root_serves_the_built_react_page(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    monkeypatch.setattr(app_module, "_PAGE", StaticFiles(directory=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "<div id='root'></div>" in response.text


def test_root_says_how_to_build_when_the_page_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "_PAGE", StaticFiles(directory=tmp_path / "dist", check_dir=False))

    response = client.get("/")

    assert response.status_code == 503
    assert "npm run build" in response.text


def test_the_browser_checks_for_a_newer_page_every_time(monkeypatch, tmp_path):
    """A rebuilt page must show without a hard refresh (Ctrl+F5)."""
    (tmp_path / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    monkeypatch.setattr(app_module, "_PAGE", StaticFiles(directory=tmp_path))
    first = client.get("/")
    assert first.headers["cache-control"] == "no-cache"

    again = client.get("/", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304
    assert again.headers["cache-control"] == "no-cache"

    monkeypatch.setattr(app_module, "_PAGE", StaticFiles(directory=tmp_path / "dist", check_dir=False))
    assert client.get("/").headers["cache-control"] == "no-cache"


def test_uploads_need_no_switch():
    pdf = ("files", ("doc.pdf", b"%PDF-1.4 not really", "application/pdf"))

    assert client.post("/api/batch", files=[pdf]).status_code == 200


def test_the_old_pages_are_gone():
    """The demo routes, and /classic once the React page had Edit and display mode."""
    for path in ("/api/mode", "/app/", "/classic", "/static/index.html"):
        assert client.get(path).status_code == 404, path
