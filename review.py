"""
Review gate — decides whether a classification can stand on its own or has to
go to a person first, and says WHY.

Ground rule #2: nothing files silently, and low confidence routes to
`_Needs review` with a reason. Before this, the only thresholds in the system
were two numbers in static/index.html — `confidence >= 0.75` and `>= 0.5` —
which made the rule that decides whether a human looks at a client's advice
record a presentational detail of one browser page, invisible to the API and
to anything else that ever consumes it.

Everything here is read from knowledge_base.json's `review_policy`
(CLAUDE.md rule #1). The thresholds are a domain judgement about the cost of
being wrong per document type, not a measurement — `calibration_status` in
that block says so, and says what would have to happen to make them one.

A document that needs review is NEVER discarded, and never loses its working:
it keeps its proposed type, its confidence and its matched signals. A reviewer
confirming a correct low-confidence answer is exactly the failure-log evidence
ground rule #6 exists to collect.
"""

import json
import re

from failure_log import log_failure

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["review_policy"]
_THRESHOLDS = _POLICY["thresholds"]
_DEFAULT = _POLICY["default_threshold"]
_REASONS = _POLICY["reason_codes"]
_FORCES_REVIEW = _KB["edge_case_flags"]["severity_forces_review"]

REVIEW_DESTINATION = _POLICY["destination"]
_CORRECTION_REASONS = _POLICY["correction_reasons"]["codes"]
_DOC_IDS = {doc["id"] for doc in _KB["documents"]}

# What /ingest hands out as document_id: a SHA-256 of the file's bytes. Only
# this shape is accepted, because a real filename is not de-identified —
# "Nguyen SOA 2024.pdf" is a client name with an extension on it.
_DOCUMENT_ID = re.compile(r"[0-9a-f]{64}")


def threshold_for(doc_type: str | None) -> float:
    """The confidence a type must reach to stand on its own.

    Falls back to the default for any type without its own entry, so adding a
    document type to the knowledge base needs no edit here.
    """
    entry = _THRESHOLDS.get(doc_type)
    return entry["value"] if entry else _DEFAULT


def _reason(code: str, detail: str) -> dict:
    return {"code": code, "why": _REASONS[code], "detail": detail}


def assess(
    *,
    in_scope: bool,
    classification: dict | None,
    flags: list[dict] | None = None,
    parse_error: str | None = None,
    has_selectable_text: bool = True,
) -> dict:
    """Whether this document needs a human, and what to tell them.

    Reasons accumulate rather than short-circuit: a low-confidence document
    that also tripped a high-severity flag has two things wrong with it, and a
    reviewer should see both rather than whichever the code checked first.
    """
    flags = flags or []
    reasons = []

    # Most specific first. These three are routinely collapsed into "we
    # couldn't file it", and they are different situations a reviewer acts on
    # differently: nothing was read, versus it was read and held no text,
    # versus it was read in full and looked like nothing we model.
    if parse_error:
        reasons.append(_reason("unreadable", parse_error))
        return _result(reasons, threshold=None, confidence=None)

    if not has_selectable_text:
        # A scanned Statement of Advice is still a Statement of Advice.
        # Calling it out of scope is exactly what #22 was about.
        reasons.append(
            _reason("no_selectable_text", "The file opened but carries no extractable text.")
        )
        return _result(reasons, threshold=None, confidence=None)

    if not in_scope:
        # Previously the end of the road — no type, no confidence, no flag,
        # indistinguishable from an unreadable file. Something arrived and
        # could not be placed; that is a review item, not a dead end.
        reasons.append(_reason("out_of_scope", "No title pattern matched at the scope gate."))
        return _result(reasons, threshold=None, confidence=None)

    classification = classification or {}

    if classification.get("classifier_error"):
        # A property of the runtime, not of the document. Kept separate so it
        # can never be recorded against the document as a classification
        # failure it did not cause.
        reasons.append(
            _reason("classifier_unavailable", classification["classifier_error"])
        )
        return _result(reasons, threshold=None, confidence=None)

    doc_type = classification.get("doc_type")
    confidence = classification.get("confidence", 0.0)
    threshold = threshold_for(doc_type)

    if doc_type is None:
        reasons.append(
            _reason("unknown_type", "The scope gate matched a title pattern, but the classifier named no type.")
        )
    elif confidence < threshold:
        reasons.append(
            _reason(
                "low_confidence",
                f"{confidence:.2f} is below the {threshold:.2f} this type has to reach.",
            )
        )

    # A rule may override its severity's default. multi_doc_bundle is medium,
    # which normally attaches a question without blocking — but filing a
    # two-document bundle as one document destroys a record rather than
    # mislabelling one, and cannot be corrected later from what was filed.
    # The override lives on the rule in the knowledge base, not here.
    def _blocks(flag: dict) -> bool:
        override = flag.get("forces_review")
        if override is not None:
            return bool(override)
        return bool(_FORCES_REVIEW.get(flag.get("severity"), False))

    blocking = [f for f in flags if _blocks(f)]
    if blocking:
        reasons.append(
            _reason(
                "flagged_blocking",
                ", ".join(sorted(f["id"] for f in blocking)),
            )
        )

    return _result(reasons, threshold=threshold, confidence=confidence)


def _result(reasons: list[dict], threshold: float | None, confidence: float | None) -> dict:
    return {
        "needs_review": bool(reasons),
        "reasons": reasons,
        "threshold": threshold,
        "confidence": confidence,
        "destination": REVIEW_DESTINATION if reasons else None,
    }


class CorrectionRejected(ValueError):
    """A reviewer's verdict that cannot be written as it stands. Raised rather
    than written, because a log that accepts anything stops being evidence."""


def record_correction(
    *,
    document_id: str,
    predicted_type: str | None,
    correct_type: str,
    reason: str,
    corrections: list[dict] | None = None,
) -> None:
    """Write a reviewer's verdict on one document to the failure log.

    The other half of assess(): that decides a person must look, this records
    what they decided. It records a judgement and files nothing, so it stays
    available in observe-only mode (#20) — that mode is when the comparison is
    most worth capturing.

    Confirmations are written too, not only corrections. The thresholds in
    review_policy are a domain guess until the failure log says otherwise,
    and a type that is confirmed every time it is held is evidence its
    threshold is set too high.

    The note is the reason code and nothing else. There is no free-text field
    anywhere in this path — the reason the de-identification rule in
    failure_log.py is a shape and not a warning.
    """
    if not isinstance(document_id, str) or not _DOCUMENT_ID.fullmatch(document_id):
        raise CorrectionRejected(
            "document_id must be the SHA-256 /ingest returned, not a filename "
            "or a path — a filename can carry a client's name."
        )
    if predicted_type is not None and predicted_type not in _DOC_IDS:
        raise CorrectionRejected(f"unknown predicted_type {predicted_type!r}")
    if correct_type not in _DOC_IDS:
        raise CorrectionRejected(
            f"unknown correct_type {correct_type!r}. A document the knowledge "
            f"base does not model cannot be recorded against a type it lacks — see #23."
        )
    if reason not in _CORRECTION_REASONS:
        raise CorrectionRejected(
            f"unknown reason {reason!r}; known reasons are {sorted(_CORRECTION_REASONS)}"
        )

    corrections = corrections or []
    same_type = predicted_type == correct_type
    if reason == "confirmed" and not same_type:
        raise CorrectionRejected(
            "reason 'confirmed' means the tool's type was right, but correct_type "
            "differs from predicted_type."
        )
    if reason != "confirmed" and same_type and not corrections:
        raise CorrectionRejected(
            f"reason {reason!r} says something was wrong, but the type is unchanged "
            f"and nothing else was corrected. Use 'confirmed', or record what changed."
        )

    try:
        log_failure(
            document_id,
            predicted_type,
            correct_type,
            f"reviewer:{reason}",
            corrections=corrections,
        )
    except ValueError as e:
        # An unknown correction kind or an extra field — failure_log.py's own
        # guard. Surfaced as the same rejection, so a caller has one thing to catch.
        raise CorrectionRejected(str(e)) from e
