"""Unit tests for parser.py — parse_pdf() against the real sample PDFs.

Run from anywhere with: pytest (root conftest.py puts the project root on
sys.path; paths here are built from this file's location, not cwd).
"""

from pathlib import Path

import pytest

from parser import parse_pdf

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_PDFS = sorted(SAMPLES_DIR.glob("*.pdf"))


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
    pdf_path = SAMPLE_PDFS[0]
    with open(pdf_path, "rb") as f:
        result = parse_pdf(f, pdf_path.name)

    assert set(result.keys()) == {
        "filename",
        "page_count",
        "char_count",
        "has_selectable_text",
        "extracted_text",
    }
