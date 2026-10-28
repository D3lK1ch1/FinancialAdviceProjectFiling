"""A failure shows a person a plain sentence, never the exception's own text.

CodeQL flagged app.py for "information exposure through an exception": the
raw text of a PDF or Ollama failure reached the response, and it can show file
paths, library versions and the machine's network setup. The full text now
goes to the server log, keyed by the document's hash and never its filename.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

_NOT_A_PDF = b"this is not a pdf at all"
# What requests raises when Ollama isn't running on Windows: a host, a port
# and an OS error number, none of which a reviewer should be shown.
_OLLAMA_DOWN = ("HTTPConnectionPool(host='localhost', port=11434): Max retries exceeded "
                "(Caused by NewConnectionError('[WinError 10061] No connection could be made'))")
_LEAKS = ("11434", "WinError", "HTTPConnectionPool", "localhost", "PdfReadError", "EOF marker")


@pytest.fixture(autouse=True)
def known_engine(monkeypatch):
    """The real engine_identity asks Ollama; these tests are about what fails, not who answers."""
    monkeypatch.setattr("app.engine_identity", lambda: {
        "model": "llama3.1", "model_digest": "46e0c10c", "ollama_version": "0.40.6",
    })


def _ingest(contents=_NOT_A_PDF):
    return client.post("/ingest", files={"file": ("Baker_George SOA.pdf", contents, "application/pdf")}).json()


def test_a_pdf_that_cannot_be_opened_gets_a_plain_reason(caplog):
    body = _ingest()

    assert body["parse_error"] == "This PDF couldn't be opened. It may be password-protected, damaged or not a PDF."
    [reason] = body["review"]["reasons"]
    assert reason["code"] == "unreadable"
    assert reason["detail"] == body["parse_error"]
    text = json.dumps(body)
    for leak in _LEAKS:
        assert leak not in text, leak
    # pypdf's own words reach the log, under the document's hash, not its name.
    assert "unreadable for document " + body["document_id"][:12] in caplog.text
    assert "Baker" not in caplog.text


def test_an_unreachable_classifier_gets_a_plain_reason(monkeypatch, caplog):
    monkeypatch.setattr("app.parse_pdf", lambda stream, filename: {
        "filename": filename, "page_count": 1, "char_count": 30, "has_selectable_text": True,
        "extracted_text": "Statement of Advice for a client", "pages": ["Statement of Advice for a client"],
        "parse_error": None,
    })
    monkeypatch.setattr("app.classify", lambda text: {
        "doc_type": None, "confidence": 0.0, "matched_signals": [], "classifier_error": _OLLAMA_DOWN,
    })
    body = _ingest()

    assert body["in_scope"] is True
    assert body["classification"]["classifier_error"] == "Ollama didn't answer"
    assert [r["code"] for r in body["review"]["reasons"]] == ["classifier_unavailable"]
    text = json.dumps(body)
    for leak in _LEAKS:
        assert leak not in text, leak
    assert "WinError 10061" in caplog.text


def test_the_batch_page_gets_no_exception_text_either():
    files = [("files", ("one.pdf", _NOT_A_PDF, "application/pdf"))]
    text = json.dumps(client.post("/api/batch", files=files).json())

    for leak in _LEAKS:
        assert leak not in text, leak
