"""/ingest returns the client names a document gives (#6). No `samples/`, no Ollama:
the PDFs are built in the test and carry no title, so the classifier is never called.
"""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app import app

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


def _ingest(pdf: bytes) -> dict:
    return client.post("/ingest", files={"file": ("doc.pdf", pdf, "application/pdf")}).json()


def test_ingest_returns_the_labelled_client_name_and_its_page():
    [candidate] = _ingest(_pdf("Client name: George Baker"))["client_candidates"]

    assert candidate["raw"] == "George Baker"
    assert candidate["page"] == 1


def test_client_candidates_is_present_and_empty_when_no_name_is_labelled():
    """A missing key and an empty list read the same to a caller; 'none found' is a result."""
    assert _ingest(_pdf(None))["client_candidates"] == []


def test_a_found_name_does_not_change_the_review_decision():
    """Nothing selects a client yet, so a name must not make a document look safer to file."""
    with_name = _ingest(_pdf("Client name: George Baker"))["review"]
    without = _ingest(_pdf("Something else entirely"))["review"]

    assert with_name == without
