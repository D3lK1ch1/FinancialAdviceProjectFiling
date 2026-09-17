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

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["review_policy"]
_THRESHOLDS = _POLICY["thresholds"]
_DEFAULT = _POLICY["default_threshold"]
_REASONS = _POLICY["reason_codes"]
_FORCES_REVIEW = _KB["edge_case_flags"]["severity_forces_review"]

REVIEW_DESTINATION = _POLICY["destination"]


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
) -> dict:
    """Whether this document needs a human, and what to tell them.

    Reasons accumulate rather than short-circuit: a low-confidence document
    that also tripped a high-severity flag has two things wrong with it, and a
    reviewer should see both rather than whichever the code checked first.
    """
    flags = flags or []
    reasons = []

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
                "flagged_high_severity",
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
