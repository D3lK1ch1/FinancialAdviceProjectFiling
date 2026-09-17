"""
Confidence verification — checks the classifier's claim about itself.

`classify()` returns a `confidence` the model assigns to its own answer. Until
now that number went straight through to whatever acted on it. It is a claim
by the model about the model, produced by the same process that produced the
answer, and nothing independent had looked at it.

Two things here can be checked without trusting the model at all:

  1. Every phrase in `matched_signals` is supposed to be text the model found
     in the document. Whether it is actually there is a fact about the
     document, not an opinion.
  2. `scope_gate.check_scope()` reads the title region deterministically from
     knowledge-base title patterns, with no model involved. It is not smarter
     than the classifier — it matches strings — but it cannot be wrong in the
     same way a language model is wrong, and that independence is what makes
     agreement between them worth more than either alone.

Verification only ever LOWERS the number (`direction_rule` in the knowledge
base). Accurate quoting shows the model told the truth about its reasoning; it
does not show the answer is right. Letting evidence raise a figure the model
invented would turn a guess into a measurement.

Both numbers survive: `confidence_raw` is the model's own, kept so drift is
visible and so the two can be compared in the failure log, and `confidence` is
what the system acts on and what review_policy's thresholds apply to.
"""

import json
import re

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["confidence_policy"]
_SIGNALS = _POLICY["signal_verification"]
_SCOPE = _POLICY["scope_agreement"]


def _normalise(text: str) -> str:
    """Remove all whitespace and casefold, so typesetting is not mistaken for
    dishonesty.

    Whitespace is removed rather than collapsed, and that is the whole point.
    PDF extraction splits words internally: the real ASIC samples yield
    "A ustralian S ecurities" and "h is advice". Collapsing runs of spaces
    does not help — the space sits inside the word — so an accurate quote from
    such a page still reads as fabricated, and the check would mark down
    almost every real PDF. A check that fires on everything gets ignored.

    The cost is that matching gets looser, and a short signal can match inside
    an unrelated word — "ROA" is inside "BROADWAY" with or without spaces.
    That is tolerable here in a way it would not be in scope_gate.py, because
    this only decides whether to LOWER confidence: a loose match declines to
    penalise, it never promotes anything. Being too eager to call a quote
    fabricated is the more damaging error, because it would send honest
    classifications of ordinary documents to review.
    """
    return re.sub(r"\s+", "", text).casefold()


def verify_signals(matched_signals: list[str], extracted_text: str) -> dict:
    """Which of the model's quoted phrases are actually in the document."""
    haystack = _normalise(extracted_text)

    found, missing = [], []
    for signal in matched_signals:
        needle = _normalise(signal)
        (found if needle and needle in haystack else missing).append(signal)

    if not matched_signals:
        return {
            "found": [],
            "missing": [],
            "proportion": None,
            "factor": _SIGNALS["no_signals_factor"],
            "note": _SIGNALS["no_signals_why"],
        }

    proportion = len(found) / len(matched_signals)
    return {
        "found": found,
        "missing": missing,
        "proportion": proportion,
        "factor": proportion,
        "note": None,
    }


def check_scope_agreement(doc_type: str | None, likely_type: str | None) -> dict:
    """Whether the deterministic title read and the model's answer agree."""
    if likely_type is None:
        # The gate reads only the first 500 characters. A document whose title
        # sits below that window leaves it silent, and silence is absence of
        # evidence — scoring it as disagreement would penalise a layout.
        return {"agrees": None, "factor": _SCOPE["no_scope_type_factor"],
                "note": _SCOPE["no_scope_type_why"]}

    agrees = doc_type == likely_type
    return {
        "agrees": agrees,
        "factor": _SCOPE["agree_factor"] if agrees else _SCOPE["disagree_factor"],
        "note": None,
    }


def verify(classification: dict, extracted_text: str, likely_type: str | None) -> dict:
    """Return the classification with a verified confidence and its working.

    The original dict is not mutated: a caller that still wants the model's
    unexamined answer can keep holding it.
    """
    verified = dict(classification)

    if verified.get("classifier_error"):
        # Nothing to verify, and nothing to lower. An unreachable classifier
        # is not a document that failed its checks.
        return verified

    raw = verified.get("confidence", 0.0) or 0.0
    signals = verify_signals(verified.get("matched_signals", []), extracted_text)
    scope = check_scope_agreement(verified.get("doc_type"), likely_type)

    acted = max(0.0, min(1.0, raw * signals["factor"] * scope["factor"]))

    verified["confidence_raw"] = raw
    verified["confidence"] = acted
    verified["verification"] = {
        "signals": signals,
        "scope_agreement": scope,
        "applied": {"raw": raw, "signal_factor": signals["factor"],
                    "scope_factor": scope["factor"], "result": acted},
    }
    return verified
