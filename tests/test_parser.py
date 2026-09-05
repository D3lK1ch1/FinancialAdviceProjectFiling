"""Unit tests for parser.py — parse_pdf() against the real sample PDFs.

Run from anywhere with: pytest (root conftest.py puts the project root on
sys.path; paths here are built from this file's location, not cwd).
"""

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from parser import parse_pdf

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_PDFS = sorted(SAMPLES_DIR.glob("*.pdf"))


def _pdf_with_pages(*page_texts: str) -> BytesIO:
    """Build a real multi-page PDF whose text pypdf can extract, using only
    project dependencies — so these tests run on a bare clone, without
    samples/ and without adding a PDF-authoring library.
    """
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 14 Tf 20 250 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)

    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


@pytest.mark.parametrize("pdf_path", SAMPLE_PDFS, ids=lambda p: p.name)
def test_parse_pdf_extracts_selectable_text(pdf_path):
    with open(pdf_path, "rb") as f:
        result = parse_pdf(f, pdf_path.name)

    assert result["filename"] == pdf_path.name
    assert result["page_count"] > 0
    assert result["has_selectable_text"] is True
    assert result["char_count"] > 0
    assert len(result["extracted_text"]) == result["char_count"]


def test_parse_pdf_returns_expected_keys():
    # Built rather than read from samples/: a key set doesn't depend on the PDF
    # being real, and samples/ isn't in git, so as a sample-backed test this one
    # raised IndexError on a bare clone instead of guarding anything.
    result = parse_pdf(_pdf_with_pages("Statement of Advice"), "generated.pdf")

    assert set(result.keys()) == {
        "filename",
        "page_count",
        "char_count",
        "has_selectable_text",
        "extracted_text",
        "pages",
    }


def test_pages_are_returned_one_per_page():
    """A firm's file is regularly one PDF holding more than one document —
    classically an SOA with the Authority to Proceed appended. Joined text
    cannot show where one ends and the next begins; the page index can.
    """
    buf = _pdf_with_pages("STATEMENT OF ADVICE", "recommendations", "AUTHORITY TO PROCEED")
    result = parse_pdf(buf, "bundle.pdf")

    assert result["page_count"] == 3
    assert len(result["pages"]) == 3
    assert result["pages"][0] == "STATEMENT OF ADVICE"
    assert result["pages"][2] == "AUTHORITY TO PROCEED"


def test_pages_reconstruct_extracted_text_exactly():
    """The two views of the file can never disagree about its contents. Pinned
    because a later change to the join — a different separator, or dropping
    empty pages — would silently break every page index derived from it.
    """
    buf = _pdf_with_pages("one", "two", "three")
    result = parse_pdf(buf, "three-pages.pdf")

    assert "\n".join(result["pages"]) == result["extracted_text"]


def test_empty_pages_are_kept_so_the_page_index_stays_true():
    """A text-less page still occupies a position. Dropping it would shift
    every page number after it, which is exactly the number a proposed split
    would be expressed in.
    """
    writer = PdfWriter()
    for _ in range(2):
        page = writer.add_blank_page(width=200, height=200)
        stream = DecodedStreamObject()
        stream.set_data(b"")
        page[NameObject("/Contents")] = writer._add_object(stream)
    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)

    result = parse_pdf(buf, "blank.pdf")

    assert result["page_count"] == 2
    assert result["pages"] == ["", ""]
    assert result["has_selectable_text"] is False
