"""Unit tests for scope_gate.py — check_scope() against the real sample PDFs.

Each sample's expected doc type is its filename prefix (FSG_*.pdf -> fsg,
etc.) — that convention is how docs/sample_documents.labelling.md ground-
truths the sample set too.
"""

from pathlib import Path

import pytest

from parser import parse_pdf
from scope_gate import check_scope

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
SAMPLE_PDFS = sorted(SAMPLES_DIR.glob("*.pdf"))


def _extract_text(pdf_path: Path) -> str:
    with open(pdf_path, "rb") as f:
        return parse_pdf(f, pdf_path.name)["extracted_text"]


@pytest.mark.parametrize("pdf_path", SAMPLE_PDFS, ids=lambda p: p.name)
def test_check_scope_matches_filename_prefix(pdf_path):
    expected_type = pdf_path.name.split("_")[0].lower()
    result = check_scope(_extract_text(pdf_path))

    assert result["in_scope"] is True
    assert result["likely_type"] == expected_type


def test_fsg_is_not_misread_as_soa():
    """Regression test for the 2026-08-22 bug: an FSG's body text explains
    what an SOA is ("you should already have a Statement of Advice..."),
    a legitimate cross-reference that isn't the document's own type. Whole-
    document scanning picked that up as an soa match; the fix scores by
    pattern length and restricts the check to the first 500 chars (title
    region). This pins that fix in place.
    """
    pdf_path = SAMPLES_DIR / "FSG_AustralianSuper.pdf"
    result = check_scope(_extract_text(pdf_path))

    assert result["likely_type"] == "fsg"


def test_check_scope_out_of_scope_text():
    text = "This is an invoice for consulting services rendered in March."
    result = check_scope(text)

    assert result == {"in_scope": False, "likely_type": None}


def test_street_address_is_not_read_as_a_document_type():
    """Regression: several title_patterns are three-letter acronyms, and the
    old bare-substring check matched "ROA" inside ROAD and BROADWAY. Every
    advice document carries a letterhead address, and it lands inside exactly
    the 500-char title window this function reads — so an out-of-scope
    document issued from a street address was pulled into the pipeline as an
    ROA. Ordinary documents, not contrived ones.
    """
    text = "Tax invoice\nIssued by Example Advice Pty Ltd\n42 BROADWAY, SYDNEY NSW 2000"

    assert check_scope(text) == {"in_scope": False, "likely_type": None}


def test_acronym_still_matches_when_it_is_the_title():
    """The boundary fix must not break the case it exists to serve: a cover
    page whose title really is the bare acronym.
    """
    assert check_scope("ROA - further advice\nPrepared 3 March 2025")["likely_type"] == "roa"
    assert check_scope("SOA prepared for the client\n1 July 2024")["likely_type"] == "soa"
