"""
The Approve / Reject buttons in the document panel (frontend/src/Inspector.jsx).

The buttons are browser code and are checked by hand. What these tests pin is
the server side of every click: the exact message each button sends is one
POST /review/correction accepts, for every choice /review/options offers. If
the knowledge base gains a type or a reason, these tests cover it with no edit.
The out-of-scope case (no proposed type, reject only) is already covered in
test_review_correction.py.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)
_DOC_ID = hashlib.sha256(b"any document bytes").hexdigest()
_OPTIONS = client.get("/review/options").json()
_TYPES = [t["id"] for t in _OPTIONS["document_types"]]
_PAGE_SOURCE = Path(__file__).parent.parent / "frontend" / "src"


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", path)
    return path


# What /ingest returned and the page sends back unchanged (#7).
_STAMP = {
    "model": "llama3.1",
    "model_digest": "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
    "ollama_version": "0.40.6",
    "kb_version": "0.3",
    "prompt_version": "a1b2c3d4e5f6",
}


def _send(predicted_type, correct_type, reason):
    """Exactly the body the page sends (see sendVerdict() in frontend/src/Inspector.jsx)."""
    return client.post("/review/correction", json={
        "document_id": _DOC_ID,
        "predicted_type": predicted_type,
        "correct_type": correct_type,
        "reason": reason,
        "engine_version": _STAMP,
    })


@pytest.mark.parametrize("doc_type", _TYPES)
def test_approve_is_accepted_for_every_type(log_path, doc_type):
    """Approve sends the proposed type back unchanged, with approve_reason."""
    res = _send(doc_type, doc_type, _OPTIONS["approve_reason"])
    assert res.status_code == 201
    [entry] = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entry["note"] == "reviewer:confirmed"


@pytest.mark.parametrize("reason", [r["code"] for r in _OPTIONS["reject_reasons"]])
def test_reject_is_accepted_for_every_reason(log_path, reason):
    """Reject sends a different type and one of the reject reasons."""
    res = _send("pds", "soa", reason)
    assert res.status_code == 201
    [entry] = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entry["note"] == f"reviewer:{reason}"


def test_reject_with_the_proposed_type_is_refused(log_path):
    """Why the reject dropdown leaves out the type the tool proposed: a
    'rejection' that keeps the same type changes nothing, and the server
    refuses it. Offering it would show the reviewer a choice that fails."""
    res = _send("pds", "pds", "lookalike")
    assert res.status_code == 422
    assert not log_path.exists()


def test_page_reads_the_choices_rather_than_keeping_a_copy():
    """The page must fetch its lists from /review/options. A type id or reason
    code written into the page is a second copy of the knowledge base, which
    goes stale the first time the knowledge base changes (ground rule #1)."""
    files = sorted(_PAGE_SOURCE.glob("*.js*"))
    assert files, "the React source is missing"
    script = "\n".join(f.read_text(encoding="utf-8") for f in files)
    assert "fetch('/review/options')" in script
    codes = [r["code"] for r in _OPTIONS["reject_reasons"]] + ["confirmed"]
    for value in codes + _TYPES:
        assert not re.search(rf"['\"`]{re.escape(value)}['\"`]", script), (
            f"{value!r} is written into the page instead of read from /review/options"
        )


def test_the_verdict_carries_the_stamp_of_the_proposal_it_judged(log_path):
    res = _send("pds", "pds", _OPTIONS["approve_reason"])
    assert res.status_code == 201
    [entry] = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert entry["engine_version"] == _STAMP


def test_a_malformed_stamp_is_a_422_not_a_500(log_path):
    res = client.post("/review/correction", json={
        "document_id": _DOC_ID,
        "predicted_type": "pds",
        "correct_type": "pds",
        "reason": _OPTIONS["approve_reason"],
        "engine_version": {**_STAMP, "model": "John Smith"},
    })
    assert res.status_code == 422
    assert not log_path.exists()
