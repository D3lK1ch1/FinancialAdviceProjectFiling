"""Unit tests for the multi_doc_bundle rule in flags.py.

Fixtures are built from plain page text, so they run on a bare clone with no
`samples/` and no Ollama. The rule was developed against real documents — see
the `evidence` fields on the rule in knowledge_base.json — and these pin the
behaviour that came out of that.
"""

import json

import pytest

from flags import evaluate_flags
from review import assess

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_RULE = {r["id"]: r for r in _KB["edge_case_flags"]["rules"]}["multi_doc_bundle"]


def _bundle(pages, doc_type="soa"):
    flags = [f for f in evaluate_flags(doc_type, "\n".join(pages), pages)
             if f["id"] == "multi_doc_bundle"]
    return flags[0] if flags else None


SOA_PAGE = "Statement of Advice prepared for J Client. Scope and basis of advice."
ATP_PAGE = "Authority to Proceed. I authorise my adviser to implement the recommendations."


def test_a_second_document_s_pagination_restarting_is_a_boundary():
    """The strong signal, and the one needing no notion of type: a document's
    own numbering starting over says a second document begins there, whatever
    either document is about. Matches the real RG 90 file, where the example
    SOA's footer restarts at "Page 1 of 23" on page 31 of 53.
    """
    pages = [f"{SOA_PAGE} Page {n} of 3" for n in (1, 2, 3)] + \
            [f"{ATP_PAGE} Page {n} of 2" for n in (1, 2)]
    flag = _bundle(pages)

    assert flag is not None
    assert any(c["page"] == 4 and c["evidence"] == "pagination_restart"
               for c in flag["candidate_boundaries"])


def test_pagination_padded_by_extraction_still_matches():
    """Real extraction pads the marker — the RG 90 sample yields
    "Page 2          of 23". Exact spacing would miss it.
    """
    pages = [f"{SOA_PAGE} Page 1      of 2", f"{SOA_PAGE} Page 2      of 2",
             f"{ATP_PAGE} Page 1        of 1"]

    assert _bundle(pages) is not None


def test_a_type_change_between_pages_is_a_boundary():
    """Matches the two real ASIC documents that carry an appended Authority to
    Proceed as their final page (CP 284 p56, RG 90 2013 p40).
    """
    flag = _bundle([SOA_PAGE, SOA_PAGE, ATP_PAGE])

    assert flag is not None
    boundary = [c for c in flag["candidate_boundaries"] if c["evidence"] == "title_transition"]
    assert boundary and boundary[0]["page"] == 3
    assert boundary[0]["detail"] == "soa -> authority_to_proceed"


def test_a_running_header_is_not_a_boundary():
    """Every page of a real SOA carries its own title in a running header, so
    presence of a type's name is not the signal — the CHANGE is. Frequency
    would be the wrong test: in a real bundle the larger document's header
    legitimately appears on most pages of the whole file.
    """
    assert _bundle([SOA_PAGE] * 12) is None


def test_a_section_inside_one_document_is_not_a_boundary():
    """The real case this came from: unisuper-flexi-pension-pds.pdf reads
    pds -> risk_profile -> pds, because a PDS has a section describing the
    risk profile of its investment options. A section hands the file back to
    its parent; an appended document does not.
    """
    pds = "Product Disclosure Statement for the Example Fund. Fees and costs."
    section = "Risk Profile of each investment option is set out below."
    pages = [pds, pds, section, section, pds, pds]

    assert _bundle(pages, doc_type="pds") is None


def test_the_return_from_an_excursion_is_not_a_boundary_either():
    """Both halves of the excursion rule are needed. Suppressing only the
    departure leaves the RETURN — risk_profile -> pds — reported as the start
    of a document, which is how this first went wrong.
    """
    pds = "Product Disclosure Statement for the Example Fund."
    section = "Risk Profile of each option."
    flag = _bundle([pds, section, pds], doc_type="pds")

    assert flag is None


def test_a_single_page_file_cannot_be_a_bundle():
    assert _bundle([SOA_PAGE]) is None
    assert _bundle([]) is None


def test_it_proposes_ranges_and_never_splits():
    """Ground rule #2 with force. A missed bundle is a flag nobody actioned; a
    wrong split cuts a record in half and nothing downstream can tell.
    """
    flag = _bundle([SOA_PAGE, SOA_PAGE, ATP_PAGE])

    assert flag["split_performed"] is False
    assert flag["proposed_split"] == [{"from_page": 1, "to_page": 2},
                                      {"from_page": 3, "to_page": 3}]
    assert flag["never_split_automatically"] == _RULE["never_split_automatically"]


def test_a_bundle_forces_review_despite_being_medium():
    """The per-rule override, and the real case that resolves
    review_policy.open_question. Medium normally attaches a question without
    blocking — but this one destroys a record rather than mislabelling one.
    """
    flag = _bundle([SOA_PAGE, SOA_PAGE, ATP_PAGE])
    assert flag["severity"] == "medium"
    assert flag["forces_review"] is True

    result = assess(
        in_scope=True,
        classification={"doc_type": "soa", "confidence": 0.99},
        flags=[flag],
    )
    assert result["needs_review"] is True
    assert "flagged_high_severity" in [r["code"] for r in result["reasons"]]


def test_a_medium_flag_without_the_override_still_does_not_block():
    """So the override is doing the work, not a change to the severity rule."""
    result = assess(
        in_scope=True,
        classification={"doc_type": "roa", "confidence": 0.99},
        flags=[{"id": "roa_basis_unconfirmed", "severity": "medium", "forces_review": None}],
    )
    assert result["needs_review"] is False


def test_detection_rules_and_their_evidence_live_in_the_knowledge_base():
    """Ground rule #1, and the `evidence` fields are what stop these numbers
    reading as arbitrary — each names the real document it was checked against.
    """
    detection = _RULE["detection"]

    assert detection["pagination_restart"]["pattern"]
    assert detection["pagination_restart"]["evidence"].strip()
    assert detection["title_transition"]["excursion_rule"].strip()
    assert detection["title_transition"]["evidence"].strip()
    assert detection["title_transition"]["known_weakness"].strip()
    assert detection["leading_region_chars"] == 500
