"""Unit tests for scope_gate.py — check_scope() against the real sample PDFs.

Each sample's expected doc type is its filename prefix (FSG_*.pdf -> fsg,
etc.) — that convention is how docs/sample_documents.labelling.md ground-
truths the sample set too.
"""

import json
from pathlib import Path

import pytest

from parser import parse_pdf
from scope_gate import IN_SCOPE_TYPES, _matcher, check_scope

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


def _longest_title_pattern(doc_id: str) -> str:
    kb_path = Path(__file__).resolve().parent.parent / "knowledge_base.json"
    kb = json.loads(kb_path.read_text())
    doc = next(d for d in kb["documents"] if d["id"] == doc_id)
    return max(doc["classifier_hints"]["title_patterns"], key=len)


@pytest.mark.parametrize("doc_id", IN_SCOPE_TYPES)
def test_all_caps_cover_page_is_recognised(doc_id):
    """#4: cover pages are routinely typeset in capitals, and a case-sensitive
    check missed "STATEMENT OF ADVICE" entirely — in_scope: False, no type, no
    flag. A document silently leaving the pipeline is worse than a wrong
    answer, because nothing surfaces for review.

    Parametrised over IN_SCOPE_TYPES and sourced from the knowledge base, so
    this covers whatever the supported set becomes without being rewritten.
    """
    title = _longest_title_pattern(doc_id)
    result = check_scope(f"{title.upper()}\nPrepared for the client, 1 July 2024")

    assert result["in_scope"] is True
    assert result["likely_type"] == doc_id


@pytest.mark.parametrize("doc_id", IN_SCOPE_TYPES)
def test_lower_case_title_is_recognised(doc_id):
    title = _longest_title_pattern(doc_id)
    result = check_scope(f"{title.lower()}\nprepared for the client, 1 july 2024")

    assert result["likely_type"] == doc_id


def test_acronym_patterns_stay_case_sensitive():
    """Case sensitivity is decided per pattern, not globally. An acronym in a
    title is capitalised; the same letters lowercase in a sentence are an
    ordinary word. Casefolding the acronyms too would make car's "CAR" pattern
    match "car loan" — entirely at home in the scope paragraph of an SOA — so
    the fix for one false negative would have bought a new false positive.
    """
    assert _matcher("CAR").search("we reviewed your car loan and car insurance") is None
    assert _matcher("CAR").search("CLIENT ADVICE RECORD (CAR)") is not None

    # Multi-word patterns go the other way: they must match in any casing.
    assert _matcher("Statement of Advice").search("STATEMENT OF ADVICE") is not None
    assert _matcher("Statement of Advice").search("statement of advice") is not None
# Every type the knowledge base defines that the code previously did not support.
# These are most of a firm's real intake, and each one used to leave the pipeline
# as in_scope: False with no type and no flag — indistinguishable from a file that
# couldn't be read at all.
NEWLY_SUPPORTED = [
    ("authority_to_proceed", "Authority to Proceed\nI authorise my adviser to implement"),
    ("fact_find", "Fact Find\nClient Data Form completed 1 July 2024"),
    ("risk_profile", "Investor Risk Profile\nAttitude to Risk questionnaire"),
    ("fee_disclosure_statement", "Fee Disclosure Statement\nOngoing Fee Consent for the period"),
]


def test_supported_types_come_from_the_knowledge_base():
    """Ground rule #1. The supported set is whatever the KB defines — asserting
    the set equality rather than a count, so the test doesn't fight a KB that
    legitimately grows.
    """
    kb_path = Path(__file__).resolve().parent.parent / "knowledge_base.json"
    kb = json.loads(kb_path.read_text())

    assert set(IN_SCOPE_TYPES) == {doc["id"] for doc in kb["documents"]}


@pytest.mark.parametrize(
    "expected_type, text", NEWLY_SUPPORTED, ids=[t for t, _ in NEWLY_SUPPORTED]
)
def test_newly_supported_types_are_recognised(expected_type, text):
    result = check_scope(text)

    assert result["in_scope"] is True
    assert result["likely_type"] == expected_type


def test_ordinary_words_do_not_match_any_document_type():
    """Kept from when `car` was a type and "CAR" was the sharpest test of the
    word-boundary work. `car` is gone — not legislated, so not carried — but the
    protection still matters: several title_patterns are three-letter acronyms
    and the words that could swallow them are ordinary English. Asserted
    negatively now, which needs no type that shouldn't exist.
    """
    for text in (
        "Client agreement\nWe act with duty of CARE at all times.",
        "Engagement letter\nSCARBOROUGH FINANCIAL PTY LTD",
        "Tax invoice\nExample Advice Pty Ltd\n42 BROADWAY, SYDNEY",
    ):
        assert check_scope(text) == {"in_scope": False, "likely_type": None}


def test_a_new_advice_record_type_needs_no_code_change():
    """DBFO Tranche 2 would replace the SOA with a successor advice record.
    That successor is deliberately NOT carried as a document type while it is
    unlegislated (`reform_watch`) — the system does not classify document types
    that are not law.

    Which means the claim that the transition is "a relabel, not a rebuild" has
    to be asserted rather than assumed, since there is no longer a placeholder
    entry standing in for it. This adds a synthetic advice-record type to a copy
    of the knowledge base and shows it classifies with no Python changed.
    """
    import importlib

    import scope_gate as sg

    kb_path = Path(__file__).resolve().parent.parent / "knowledge_base.json"
    kb = json.loads(kb_path.read_text())
    kb["documents"].append(
        {
            "id": "successor_advice_record",
            "name": "Hypothetical successor to the SOA",
            "abbrev": "SAR",
            "category": "advice_record",
            "advice_record_role": True,
            "legislation": {"primary": "hypothetical"},
            "classifier_hints": {
                "title_patterns": ["Successor Advice Record"],
                "key_fields": [],
                "distinguishing_signals": [],
                "confusable_with": [],
            },
            "links_to": [],
            "version_notes": "",
        }
    )

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "knowledge_base.json").write_text(json.dumps(kb))
        cwd = Path.cwd()
        try:
            import os

            os.chdir(tmp)
            reloaded = importlib.reload(sg)

            assert "successor_advice_record" in reloaded.IN_SCOPE_TYPES
            result = reloaded.check_scope("Successor Advice Record\nPrepared 1 July 2026")
            assert result["in_scope"] is True
            assert result["likely_type"] == "successor_advice_record"
        finally:
            os.chdir(cwd)
            importlib.reload(sg)


def test_advice_record_role_survives_the_removed_successor_type():
    """CLAUDE.md: advice_record_role is the DBFO seam and is load-bearing. It is
    still carried by more than one type after the unlegislated successor was
    removed, so role-keyed logic stays exercised and cannot rot into a field
    nothing reads.
    """
    kb_path = Path(__file__).resolve().parent.parent / "knowledge_base.json"
    kb = json.loads(kb_path.read_text())
    carriers = [d["id"] for d in kb["documents"] if d.get("advice_record_role")]

    assert len(carriers) > 1, f"the seam needs more than one carrier to stay exercised: {carriers}"
    assert "soa" in carriers



# Every advice document names other document types in its body — that's what the
# knowledge base's links_to relationships describe. The gate has to tell "this IS
# a PDS" from "this REFERS to a PDS", and it only has the title window to do it.
CROSS_REFERENCES = [
    (
        "roa",
        "Record of Advice\nFurther advice for the client, 3 March 2025.\n"
        "Please refer to the Product Disclosure Statement for the product discussed.",
    ),
    (
        "fsg",
        "Financial Services Guide\nExample Advice Pty Ltd, AFSL 123456.\n"
        "If we give you personal advice you will receive a Statement of Advice.",
    ),
    (
        "soa",
        "Statement of Advice\nPrepared for the client, 1 July 2024.\n"
        "See the Product Disclosure Statement for details of the recommended product.",
    ),
]


@pytest.mark.parametrize(
    "expected_type, text", CROSS_REFERENCES, ids=[t for t, _ in CROSS_REFERENCES]
)
def test_own_title_beats_a_longer_cross_reference(expected_type, text):
    """#4: ranking by summed pattern length made string length a stand-in for
    confidence, and a bad one. "Product Disclosure Statement" is 28 characters
    and "Record of Advice" is 16, so an ROA that refers to the PDS of the
    product it discusses — which is what an ROA does — came back as a pds.

    Ranking by earliest match position is the signal that was actually meant:
    a document's own title is at the top, a type it merely cites appears
    further down.
    """
    assert check_scope(text)["likely_type"] == expected_type


def test_more_matched_patterns_wins_a_position_tie():
    """Two types whose earliest match sits at the same offset break on how many
    distinct patterns each matched, so corroborated evidence beats a single hit.
    """
    from scope_gate import _MATCHERS  # noqa: PLC0415 — asserting the ranking input

    text = "Financial Services Guide\nPart 2 Adviser Profile\nAFSL 123456"
    matched = [p for p, rx in _MATCHERS["fsg"] if rx.search(text)]

    assert len(matched) >= 2, "fsg should match on more than one pattern here"
    assert check_scope(text)["likely_type"] == "fsg"
