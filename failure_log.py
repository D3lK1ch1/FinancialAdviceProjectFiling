"""Failure log — CLAUDE.md ground rule #6: every misclassification recorded
as input, tool's answer, correct answer, and a one-line why. This is the
improvement loop and the proof of accuracy, not optional bookkeeping.

Append-only JSON Lines file. Field names mirror 2_ARCHITECTURE.md's
`failure_log` SQLite table (document_id, predicted_type, correct_type, note,
logged_at) so this can move into SQLite later (unit #9) without a schema
rethink — it's the same shape, just not persisted there yet.

DE-IDENTIFIED BY RULE. Unlike samples/, this file is committed to git and
shared between collaborators, so it travels — and it must never carry client
identity. document_id is a filename or a hash, never a full path: a path like
"/clients/Nguyen Family/fact find.pdf" leaks a client name in the folder it
sits in even when the filename itself is clean. note describes the
classification decision only — predicted, correct, one line on why — never a
client name, an account number, a balance, or any figure read out of the
document. tests/test_failure_log.py asserts the record's exact field set, so
a field cannot be added here without that test failing first.

The restriction is on the PERSON, not the classification. The system itself
extracts client names and must — it files documents into folders named after
clients. Only this file is restricted, because only this file leaves the firm.
Advice type and advice stage are knowledge_base.json categories, not personal
information, and belong here in full.

    leaks:  {"document_id": "/Clients/Nguyen Family/2024 fact find.pdf",
             "note": "OCR poor p3, missed $840,000 super balance for Linh Nguyen"}
    clean:  {"document_id": "fact_find_2024.pdf",
             "note": "OCR poor p3, balance field not extracted"}

The leaking one was written by somebody being helpful at the end of the day,
not somebody being careless. That is the realistic failure mode, and the
reason this rule is written down instead of left to judgement.

No review UI exists yet to capture human corrections (unit #12), so the
current caller is tests/test_e2e.py: it has both a real classifier
prediction and a hand-labelled correct answer for every sample, which is
exactly the comparison this log exists to record.

CORRECTIONS BEYOND THE DOCUMENT TYPE. predicted_type/correct_type record one
kind of correction: the tool said PDS, it was a file note. Reviewers make
others. Which of the three ROA situations a record sits on is a correction
about the same document with the same weight, and the model's self-reported
confidence versus the verified one is a third. A second pair of fields per
kind would mean a schema change for every future flag, so `corrections` is a
list of {kind, predicted, correct} instead — one shape that any flag with an
answer worth keeping can use.

The de-identification rule applies to it unchanged, and is the reason the
shape is constrained rather than free-form. `kind` must be a known kind and
the values are knowledge-base categories — doc type ids, situation ids,
numbers — never text copied out of a document. A free-text field here is
exactly where a client name would eventually land, written by somebody being
helpful at the end of the day. There is no free-text field.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

FAILURE_LOG_PATH = Path(__file__).resolve().parent / "failure_log.jsonl"


# What a reviewer can be recorded as having corrected. Adding a kind is a
# deliberate act with a test behind it, not something a caller can invent:
# an unknown kind raises rather than being written, because a log that
# silently accepts anything stops being evidence of anything.
CORRECTION_KINDS = {
    "doc_type": "The document type the classifier proposed, against the one a reviewer chose.",
    "roa_situation": "Which of the three situations an ROA sits on — further_advice, no_buy_sell or small_investment. Not derivable from the document type, and it decides what the record must contain.",
    "confidence": "The confidence the system acted on, against what a reviewer judged. Kept so the model's self-reported number can be compared with the verified one over time.",
}


def _check_corrections(corrections: list[dict]) -> list[dict]:
    checked = []
    for correction in corrections:
        kind = correction.get("kind")
        if kind not in CORRECTION_KINDS:
            raise ValueError(
                f"unknown correction kind {kind!r}; known kinds are "
                f"{sorted(CORRECTION_KINDS)}. Add it to CORRECTION_KINDS "
                f"deliberately rather than writing an unrecognised one."
            )
        # Exactly three keys, and no free-text field among them. This is the
        # de-identification rule expressed as a shape: there is nowhere here
        # for a client name to be written even by accident.
        extra = set(correction) - {"kind", "predicted", "correct"}
        if extra:
            raise ValueError(
                f"correction carries unexpected field(s) {sorted(extra)}. Only "
                f"kind, predicted and correct may be recorded — see the "
                f"de-identification rule in this module's docstring."
            )
        checked.append({"kind": kind, "predicted": correction.get("predicted"),
                        "correct": correction.get("correct")})
    return checked


def log_failure(
    document_id: str,
    predicted_type: str | None,
    correct_type: str,
    note: str,
    corrections: list[dict] | None = None,
) -> None:
    entry = {
        "document_id": document_id,
        "predicted_type": predicted_type,
        "correct_type": correct_type,
        "note": note,
        # Always present, so a reader never has to branch on whether the key
        # exists. Empty means the document type was the only thing corrected.
        "corrections": _check_corrections(corrections or []),
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(FAILURE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
