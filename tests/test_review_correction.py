"""Tests for the reviewer-correction path — #4's fifth checkbox.

A reviewer's verdict reaches the failure log through record_correction() and
POST /review/correction. Plain data and a blank in-memory PDF, no `samples/`
needed, so they run on a bare clone. Every test points the log at tmp_path so
the real failure_log.jsonl is never touched.
"""

import hashlib
import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import app
from review import CorrectionRejected, record_correction

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_REASONS = _KB["review_policy"]["correction_reasons"]["codes"]
_DOC_ID = hashlib.sha256(b"any document bytes").hexdigest()

client = TestClient(app)


@pytest.fixture
def log_path(tmp_path, monkeypatch):
    path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", path)
    return path


def _entries(path):
    return [json.loads(line) for line in path.read_text().strip().splitlines()]


def _record(**overrides):
    kwargs = dict(
        document_id=_DOC_ID,
        predicted_type="pds",
        correct_type="soa",
        reason="lookalike",
    )
    kwargs.update(overrides)
    record_correction(**kwargs)


def test_a_correction_is_written_with_the_reason_as_its_note(log_path):
    _record()

    [entry] = _entries(log_path)
    assert entry["document_id"] == _DOC_ID
    assert entry["predicted_type"] == "pds"
    assert entry["correct_type"] == "soa"
    assert entry["note"] == "reviewer:lookalike"


def test_a_confirmation_is_written_too(log_path):
    """Thresholds are calibrated from confirmations as much as corrections: a
    type confirmed every time it is held is being held too often. Logging only
    the wrong answers would hide that.
    """
    _record(predicted_type="soa", correct_type="soa", reason="confirmed")

    [entry] = _entries(log_path)
    assert entry["predicted_type"] == entry["correct_type"] == "soa"
    assert entry["note"] == "reviewer:confirmed"


def test_a_document_the_tool_could_not_type_can_still_be_corrected(log_path):
    """Unreadable, no text, out of scope — the tool named nothing, and a
    reviewer naming it is the most useful correction there is.
    """
    _record(predicted_type=None, correct_type="fact_find", reason="poor_text")

    [entry] = _entries(log_path)
    assert entry["predicted_type"] is None
    assert entry["correct_type"] == "fact_find"


def test_an_roa_situation_can_be_corrected_without_the_type_changing(log_path):
    _record(
        predicted_type="roa",
        correct_type="roa",
        reason="knowledge_base_gap",
        corrections=[{"kind": "roa_situation", "predicted": "further_advice", "correct": "small_investment"}],
    )

    [entry] = _entries(log_path)
    assert entry["corrections"] == [
        {"kind": "roa_situation", "predicted": "further_advice", "correct": "small_investment"}
    ]


@pytest.mark.parametrize(
    "document_id",
    [
        "Nguyen SOA 2024.pdf",
        "/Clients/Nguyen Family/2024 fact find.pdf",
        _DOC_ID.upper(),
        _DOC_ID[:-1],
    ],
)
def test_only_the_ingest_hash_is_accepted_as_document_id(log_path, document_id):
    """A filename is not de-identified — it is routinely the client's name.
    Only the SHA-256 /ingest hands out can reach the shared log.
    """
    with pytest.raises(CorrectionRejected):
        _record(document_id=document_id)
    assert not log_path.exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"correct_type": "client_letter"},                    # not a KB type
        {"predicted_type": "statement"},                      # not a KB type
        {"reason": "the client said it was wrong"},           # free text, not a code
        {"reason": "confirmed"},                              # pds -> soa is not a confirmation
        {"predicted_type": "soa", "correct_type": "soa"},     # "lookalike", yet nothing changed
        {"corrections": [{"kind": "client_name", "predicted": "x", "correct": "y"}]},
        {"corrections": [{"kind": "doc_type", "predicted": "pds", "correct": "soa", "note": "x"}]},
    ],
)
def test_an_inconsistent_or_unknown_verdict_is_refused_not_written(log_path, overrides):
    with pytest.raises(CorrectionRejected):
        _record(**overrides)
    assert not log_path.exists()


def test_every_reason_has_a_definition_and_confirmed_exists():
    assert "confirmed" in _REASONS
    assert all(isinstance(v, str) and v.strip() for v in _REASONS.values())


# --- The API seam -----------------------------------------------------------


def _blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_ingest_returns_a_content_hash_as_document_id():
    """Same bytes, same id — whatever the file is called."""
    pdf = _blank_pdf()

    a = client.post("/ingest", files={"file": ("Nguyen SOA 2024.pdf", pdf, "application/pdf")}).json()
    b = client.post("/ingest", files={"file": ("renamed.pdf", pdf, "application/pdf")}).json()

    assert a["document_id"] == b["document_id"] == hashlib.sha256(pdf).hexdigest()


def test_an_ingest_id_can_be_sent_straight_back_as_a_correction(log_path):
    pdf = _blank_pdf()
    ingested = client.post("/ingest", files={"file": ("scan.pdf", pdf, "application/pdf")}).json()

    res = client.post(
        "/review/correction",
        json={
            "document_id": ingested["document_id"],
            "predicted_type": None,
            "correct_type": "authority_to_proceed",
            "reason": "poor_text",
        },
    )

    assert res.status_code == 201
    [entry] = _entries(log_path)
    assert entry["document_id"] == ingested["document_id"]
    assert entry["correct_type"] == "authority_to_proceed"


def test_a_refused_correction_is_a_422_with_the_reason(log_path):
    res = client.post(
        "/review/correction",
        json={
            "document_id": "Nguyen SOA 2024.pdf",
            "predicted_type": "pds",
            "correct_type": "soa",
            "reason": "lookalike",
        },
    )

    assert res.status_code == 422
    assert "filename" in res.json()["detail"]
    assert not log_path.exists()
