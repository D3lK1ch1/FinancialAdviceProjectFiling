"""Unit tests for confidence.py — verifying the classifier's claim about itself.

Plain data, no `samples/` and no Ollama, so they run on a bare clone.
"""

import json

import pytest

from confidence import check_scope_agreement, verify, verify_signals

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["confidence_policy"]

TEXT = (
    "STATEMENT OF ADVICE prepared for Jane Client.\n"
    "Scope of advice: retirement and superannuation consolidation.\n"
    "Date of advice: 14 March 2024."
)


def _verify(doc_type="soa", confidence=0.9, signals=None, likely_type="soa"):
    return verify(
        {"doc_type": doc_type, "confidence": confidence,
         "matched_signals": [] if signals is None else signals},
        TEXT,
        likely_type,
    )


def test_an_honest_confident_answer_is_left_alone():
    """Every quote real, and the deterministic title read agrees. Nothing here
    justifies lowering the model's number.
    """
    result = _verify(signals=["Statement of Advice", "Scope of advice"])

    assert result["confidence"] == pytest.approx(0.9)
    assert result["confidence_raw"] == 0.9
    assert result["verification"]["signals"]["missing"] == []


def test_a_quote_that_is_not_in_the_document_lowers_the_number():
    """The check that matters. A model naming a phrase the document doesn't
    contain has given reasoning that doesn't hold, and the system should act
    on less than it was told.
    """
    result = _verify(signals=["Statement of Advice", "Authority to Proceed"])

    assert result["verification"]["signals"]["missing"] == ["Authority to Proceed"]
    assert result["confidence"] == pytest.approx(0.45)
    assert result["confidence_raw"] == 0.9, "the model's own number must survive unchanged"


def test_an_answer_with_no_quotes_at_all_is_discounted_but_not_rejected():
    """An answer with no working. Not a fabrication, so not zero — the flag
    and the review threshold still get to see the proposal.
    """
    result = _verify(signals=[])

    assert result["confidence"] == pytest.approx(0.9 * _POLICY["signal_verification"]["no_signals_factor"])
    assert result["verification"]["signals"]["proportion"] is None


def test_disagreeing_with_the_scope_gate_lowers_the_number():
    """Two independent readings disagree. The gate is not smarter — it matches
    title strings — but it cannot be wrong the same way a language model is,
    and that is what makes the disagreement informative.
    """
    result = _verify(doc_type="pds", signals=["Statement of Advice"], likely_type="soa")

    assert result["verification"]["scope_agreement"]["agrees"] is False
    assert result["confidence"] == pytest.approx(0.9 * _POLICY["scope_agreement"]["disagree_factor"])


def test_a_silent_scope_gate_is_not_disagreement():
    """The gate reads only the first 500 characters, so a document whose title
    sits below that window leaves it with no opinion. Absence of evidence must
    not be scored as evidence of absence — that would penalise a layout.
    """
    result = _verify(signals=["Statement of Advice"], likely_type=None)

    assert result["verification"]["scope_agreement"]["agrees"] is None
    assert result["confidence"] == pytest.approx(0.9)


def test_verification_can_only_lower_never_raise():
    """`direction_rule`. Accurate quoting shows the model told the truth about
    its reasoning, not that the answer is right. Letting evidence inflate a
    number the model invented would launder a guess into a measurement.
    """
    for raw in (0.1, 0.5, 0.9, 1.0):
        for signals in ([], ["Statement of Advice"], ["Statement of Advice", "Scope of advice"]):
            for likely in ("soa", "pds", None):
                result = verify(
                    {"doc_type": "soa", "confidence": raw, "matched_signals": signals},
                    TEXT, likely,
                )
                assert result["confidence"] <= raw + 1e-9, (raw, signals, likely)
                assert 0.0 <= result["confidence"] <= 1.0


def test_the_two_numbers_are_kept_separately():
    """`two_numbers`: the model's own figure survives so drift is visible and
    the two can be compared in the failure log.
    """
    result = _verify(signals=["Authority to Proceed"])

    assert result["confidence_raw"] == 0.9
    assert result["confidence"] < result["confidence_raw"]
    assert result["verification"]["applied"]["raw"] == 0.9


def test_pdf_typesetting_is_not_mistaken_for_a_made_up_quote():
    """The real reason matching is normalised rather than exact. Extraction
    from the actual ASIC samples produces "A ustralian S ecurities" and "h is
    advice" — under exact matching an accurate quote from such a page reads as
    fabricated, punishing the document's typesetting rather than the model.
    """
    mangled = "The A ustralian S ecurities and I nvestments C ommission has prepared this."
    result = verify_signals(["Australian Securities and Investments Commission"], mangled)

    assert result["missing"] == []
    assert result["proportion"] == 1.0


def test_matching_ignores_case_and_line_breaks():
    wrapped = "Statement of\nAdvice prepared for Jane Client."

    assert verify_signals(["STATEMENT OF ADVICE"], wrapped)["missing"] == []


def test_an_unreachable_classifier_is_not_marked_down():
    """Nothing to verify, and nothing to lower — a runtime failure is not a
    document that failed its checks. review.py gives it its own reason code.
    """
    broken = {"doc_type": None, "confidence": 0.0, "matched_signals": [],
              "classifier_error": "timed out"}
    result = verify(broken, TEXT, "soa")

    assert "verification" not in result
    assert "confidence_raw" not in result


def test_the_original_classification_is_not_mutated():
    """A caller still holding the model's unexamined answer keeps it."""
    original = {"doc_type": "soa", "confidence": 0.9, "matched_signals": ["Authority to Proceed"]}
    verify(original, TEXT, "soa")

    assert original == {"doc_type": "soa", "confidence": 0.9,
                        "matched_signals": ["Authority to Proceed"]}


def test_both_checks_compound():
    """A model that invented half its quotes AND disagrees with the title read
    has two independent things wrong with it.
    """
    result = _verify(doc_type="pds", signals=["Statement of Advice", "not in here at all"],
                     likely_type="soa")

    expected = 0.9 * 0.5 * _POLICY["scope_agreement"]["disagree_factor"]
    assert result["confidence"] == pytest.approx(expected)


def test_the_factors_come_from_the_knowledge_base():
    """Ground rule #1 — these are domain judgements, not constants in Python,
    and `calibration_status` records that they are judgements rather than
    fitted values.
    """
    assert 0.0 < _POLICY["signal_verification"]["no_signals_factor"] < 1.0
    assert 0.0 < _POLICY["scope_agreement"]["disagree_factor"] < 1.0
    assert _POLICY["scope_agreement"]["agree_factor"] == 1.0, "agreement must not inflate"
    assert _POLICY["scope_agreement"]["no_scope_type_factor"] == 1.0, "silence must not penalise"
    assert _POLICY["calibration_status"].strip()


def test_scope_agreement_helper_reports_its_own_reasoning():
    assert check_scope_agreement("soa", "soa")["agrees"] is True
    assert check_scope_agreement("soa", "pds")["agrees"] is False
    assert check_scope_agreement("soa", None)["note"], "silence should explain itself"
