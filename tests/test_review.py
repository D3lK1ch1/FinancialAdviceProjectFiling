"""Unit tests for review.py — the needs_review decision and its reasons.

Plain data, no `samples/` needed, so they run on a bare clone.
"""

import json

import pytest

from review import assess, threshold_for

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["review_policy"]
_DOC_IDS = [doc["id"] for doc in _KB["documents"]]


def _ok(doc_type, confidence):
    return assess(in_scope=True, classification={"doc_type": doc_type, "confidence": confidence})


def _codes(result):
    return [r["code"] for r in result["reasons"]]


def test_out_of_scope_is_a_review_reason_not_a_dead_end():
    """#4's fourth checkbox, and the behaviour it was written against: an
    out-of-scope document used to leave the pipeline with no type, no
    confidence and no flag — indistinguishable from an unreadable file.
    Something arrived and could not be placed, which is a review item.
    """
    result = assess(in_scope=False, classification=None)

    assert result["needs_review"] is True
    assert _codes(result) == ["out_of_scope"]
    assert result["destination"] == _POLICY["destination"]


def test_a_confident_classification_needs_nobody():
    result = _ok("soa", 0.91)

    assert result["needs_review"] is False
    assert result["reasons"] == []
    assert result["destination"] is None


def test_the_same_confidence_passes_for_one_type_and_not_another():
    """The whole point of per-type thresholds. A single global number treats
    every document as equally expensive to misplace: misfiling a PDS moves a
    product brochure, misfiling an SOA builds an advice event around the wrong
    document.
    """
    borderline = 0.72

    assert _ok("soa", borderline)["needs_review"] is True
    assert _ok("pds", borderline)["needs_review"] is False

    assert threshold_for("soa") > threshold_for("pds")


def test_a_low_confidence_document_keeps_its_working():
    """It is not discarded and not blanked. A reviewer confirming a correct
    low-confidence answer is exactly the failure-log evidence ground rule #6
    exists to collect, and that needs the proposal to still be there.
    """
    result = _ok("soa", 0.55)

    assert _codes(result) == ["low_confidence"]
    assert result["confidence"] == 0.55
    assert result["threshold"] == 0.8
    assert "0.55" in result["reasons"][0]["detail"]
    assert "0.80" in result["reasons"][0]["detail"]


def test_confidence_exactly_on_the_threshold_passes():
    """Meets-or-exceeds, as `threshold_meaning` says. Pinned because an
    off-by-one here silently sends a whole type's worth of documents to review.
    """
    assert _ok("soa", 0.8)["needs_review"] is False
    assert _ok("soa", 0.79)["needs_review"] is True


def test_an_unnamed_type_is_distinct_from_out_of_scope():
    """Both mean "no type", and they are different situations: out_of_scope
    means nothing looked like ours, unknown_type means the title gate DID
    match and the classifier still could not name it.
    """
    result = assess(in_scope=True, classification={"doc_type": None, "confidence": 0.0})

    assert _codes(result) == ["unknown_type"]


def test_an_unreachable_classifier_is_not_the_document_s_fault():
    """Kept as its own reason so it can never be recorded against the document
    as a classification failure it did not cause.
    """
    result = assess(
        in_scope=True,
        classification={"doc_type": None, "confidence": 0.0, "classifier_error": "timed out"},
    )

    assert _codes(result) == ["classifier_unavailable"]
    assert result["reasons"][0]["detail"] == "timed out"


def test_a_high_severity_flag_forces_review_on_its_own():
    """A confident classification is not enough if something high-severity
    fired. edge_case_flags exists to route documents to review.
    """
    result = assess(
        in_scope=True,
        classification={"doc_type": "authority_to_proceed", "confidence": 0.95},
        flags=[{"id": "atp_without_advice_record", "severity": "high"}],
    )

    assert result["needs_review"] is True
    assert _codes(result) == ["flagged_blocking"]
    assert "atp_without_advice_record" in result["reasons"][0]["detail"]


def test_a_medium_flag_attaches_a_question_without_blocking():
    """roa_basis_unconfirmed fires on EVERY ROA. If medium blocked, every ROA
    would need review and the queue would be ignored — the failure mode named
    in #20's direction note. The question still travels with the document; it
    just doesn't gate it. See review_policy.open_question.
    """
    result = assess(
        in_scope=True,
        classification={"doc_type": "roa", "confidence": 0.88},
        flags=[{"id": "roa_basis_unconfirmed", "severity": "medium"}],
    )

    assert result["needs_review"] is False


def test_reasons_accumulate_rather_than_short_circuit():
    """Two things wrong with a document is two things a reviewer should see,
    not whichever the code happened to check first.
    """
    result = assess(
        in_scope=True,
        classification={"doc_type": "soa", "confidence": 0.4},
        flags=[{"id": "risk_mismatch", "severity": "high"}],
    )

    assert _codes(result) == ["low_confidence", "flagged_blocking"]


def test_a_type_with_no_entry_falls_back_to_the_default():
    """So adding a document type to the knowledge base needs no edit to
    review_policy (ground rule #1). `file_note` is the live case — it lands in
    #23 and has no threshold of its own.
    """
    assert "file_note" not in _POLICY["thresholds"]
    assert threshold_for("file_note") == _POLICY["default_threshold"]
    assert threshold_for(None) == _POLICY["default_threshold"]


def test_every_threshold_names_a_real_document_type():
    """A threshold for a type that does not exist is a rule nothing can ever
    apply — the same class of defect #27 fixed in the stage map.
    """
    for doc_type in _POLICY["thresholds"]:
        assert doc_type in _DOC_IDS, doc_type


def test_every_threshold_carries_its_reasoning():
    """These numbers are a domain judgement, not a measurement
    (`calibration_status` says so). A bare number nobody can argue with is
    what makes it un-revisable later.
    """
    for doc_type, entry in _POLICY["thresholds"].items():
        assert 0.0 < entry["value"] <= 1.0, doc_type
        assert entry["why"].strip(), doc_type


def test_advice_records_are_held_to_the_highest_bar():
    """The domain claim the numbers encode, asserted rather than left implied:
    the advice record is the centre of an advice event, so it is the most
    expensive thing to misplace.
    """
    advice_records = [d["id"] for d in _KB["documents"] if d.get("advice_record_role")]
    others = [d["id"] for d in _KB["documents"] if not d.get("advice_record_role")]

    assert advice_records, "advice_record_role should still identify the advice records"
    assert min(threshold_for(d) for d in advice_records) >= max(
        threshold_for(d) for d in others
    )


@pytest.mark.parametrize("code", ["out_of_scope", "unknown_type", "low_confidence",
                                  "classifier_unavailable", "flagged_blocking"])
def test_every_reason_code_explains_itself_from_the_knowledge_base(code):
    """Ground rule #1: the explanation a reviewer reads is data, not a string
    in Python.
    """
    assert _POLICY["reason_codes"][code].strip()
