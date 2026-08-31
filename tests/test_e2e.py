"""End-to-end test — POST /ingest through the real FastAPI app, exercising
the full parse -> scope_gate -> classify pipeline.

Unlike test_classifier.py, this hits a REAL local Ollama (localhost:11434,
model "llama3.1") — no mocking. That's a deliberate choice: this is the one
test that proves the whole wired pipeline actually works end to end, not
just each piece in isolation. It needs Ollama running with llama3.1 pulled
to pass; it fails loudly (not a silent skip) if that's not the case, since
"classifier unreachable" is exactly the kind of integration break this test
exists to catch.
"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app import app
from failure_log import log_failure

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
client = TestClient(app)

ONE_SAMPLE_PER_TYPE = [
    ("fsg", "FSG_AustralianSuper.pdf"),
    ("pds", "PDS_AustralianSuper.pdf"),
    ("roa", "ROA_INFO266_att1_retain_modify.pdf"),
    ("soa", "SOA_RG90_scaled_advice.pdf"),
]


@pytest.mark.parametrize("expected_type, filename", ONE_SAMPLE_PER_TYPE, ids=[t for t, _ in ONE_SAMPLE_PER_TYPE])
def test_ingest_full_pipeline_in_scope(expected_type, filename):
    pdf_path = SAMPLES_DIR / filename

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/ingest",
            files={"file": (filename, f, "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()

    assert body["in_scope"] is True
    assert body["likely_type"] == expected_type

    classification = body["classification"]
    predicted_type = classification.get("doc_type")

    if "classifier_error" in classification or predicted_type != expected_type:
        log_failure(
            document_id=filename,
            predicted_type=predicted_type,
            correct_type=expected_type,
            note=classification.get("classifier_error", "doc_type mismatch on live classification"),
        )

    assert "classifier_error" not in classification, classification.get("classifier_error")
    assert classification["doc_type"] == expected_type
    assert 0.0 <= classification["confidence"] <= 1.0
    assert isinstance(classification["matched_signals"], list)
    assert len(classification["matched_signals"]) > 0


def test_ingest_out_of_scope_skips_classification():
    # add_blank_page() alone gives a page with no /Contents key at all, which
    # crashes pypdf's layout-mode extract_text() (KeyError: '/Contents') —
    # a real pypdf edge case, but not the one this test is for. An explicit
    # empty content stream mimics a real text-less (e.g. scanned) page
    # without tripping that.
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    stream = DecodedStreamObject()
    stream.set_data(b"")
    page[NameObject("/Contents")] = writer._add_object(stream)

    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)

    response = client.post(
        "/ingest",
        files={"file": ("blank.pdf", buf, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["has_selectable_text"] is False
    assert body["in_scope"] is False
    assert body["likely_type"] is None
    assert "classification" not in body
