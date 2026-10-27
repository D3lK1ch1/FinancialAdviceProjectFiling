"""One address for the tool: the React page at /, the previous page at /classic.

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
    assert "/classic" in response.text


def test_the_previous_page_is_at_classic():
    response = client.get("/classic")

    assert response.status_code == 200
    assert "/ingest" in response.text


def test_uploads_need_no_switch():
    pdf = ("files", ("doc.pdf", b"%PDF-1.4 not really", "application/pdf"))

    assert client.post("/api/batch", files=[pdf]).status_code == 200


def test_the_demo_routes_are_gone():
    assert client.get("/api/mode").status_code == 404
    assert client.get("/app/").status_code == 404
