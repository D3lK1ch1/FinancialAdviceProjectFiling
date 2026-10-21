"""/api/batch and manifest.py: the shape the React page reads (frontend/README.md).

No `samples/`, no Ollama: the PDFs are built in the test and carry no title, so
the classifier is never called.
"""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app import app
from manifest import build_manifest

client = TestClient(app)


def _pdf(text: str | None) -> bytes:
    """Duplicated from tests/test_dates.py, per the one-file-one-concern test style."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text is not None:
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 14 Tf 20 250 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _result(**filing) -> dict:
    """A minimal /ingest result: an SOA the reviewer need not hold."""
    return {
        "document_id": "a" * 64,
        "filename": "scan_004.pdf",
        "page_count": 1,
        "classification": {"doc_type": "soa", "confidence": 0.97, "matched_signals": ["Statement of Advice"]},
        "review": {"needs_review": False, "reasons": [], "threshold": 0.9},
        "flags": [],
        "filing": {"client_reason": "read from document", "event_reason": "advice record", "stages": [],
                   "filename": "2024-03-14 SOA.pdf", **filing},
    }


def test_batch_returns_one_manifest_with_every_document():
    files = [("files", ("one.pdf", _pdf(None), "application/pdf")),
             ("files", ("two.pdf", _pdf("Client name: George Baker"), "application/pdf"))]
    body = client.post("/api/batch", files=files).json()

    manifest = body["local"]["default"]
    assert [d["source_name"] for d in manifest["documents"]] == ["one.pdf", "two.pdf"]
    assert manifest["batch"]["documents"] == 2


def test_a_path_is_only_joined_when_every_part_is_known():
    """A path with a hole in it reads as a real destination (filing.proposed_filing)."""
    [doc] = build_manifest([_result(client_folder=None, event_folder="2024-03 — Retirement")])["local"]["default"]["documents"]

    assert doc["destination"]["path"] is None
    assert "read from document" in doc["destination"]["rationale"]


def test_a_complete_proposal_gets_its_path_and_opens_its_event():
    manifest = build_manifest([_result(client_folder="Nguyen, Lan", event_folder="2024-03 — Retirement")])["local"]["default"]
    [doc] = manifest["documents"]
    [event] = manifest["events"]

    assert doc["destination"]["path"] == "Nguyen, Lan/2024-03 — Retirement/2024-03-14 SOA.pdf"
    assert doc["event_id"] == event["event_id"]
    assert (event["date"], event["subject"]) == ("2024-03", "Retirement")


def test_each_document_keeps_its_own_threshold():
    """The backend sets a line per type (review_policy.thresholds); the page draws that one."""
    [doc] = build_manifest([_result()])["local"]["default"]["documents"]

    assert doc["threshold"] == 0.9
