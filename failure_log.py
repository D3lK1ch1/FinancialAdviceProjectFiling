"""Failure log — CLAUDE.md ground rule #6: every misclassification recorded
as input, tool's answer, correct answer, and a one-line why. This is the
improvement loop and the proof of accuracy, not optional bookkeeping.

Append-only JSON Lines file. Field names mirror archive/2_ARCHITECTURE.md's
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

Two callers. A reviewer's verdict arrives through review.record_correction()
(POST /review/correction), with document_id the SHA-256 /ingest returned and
note a reason code from knowledge_base.json — never typed. tests/test_e2e.py
is the other: it has a real classifier prediction and a hand-labelled correct
answer for every public sample.

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

WHICH ENGINE (#7). A verdict measures one classifier: one model's exact
weights, one Ollama runtime, one knowledge-base version, one prompt. When any
of those changes, earlier verdicts measure something that no longer runs, and
an accuracy figure that mixes them describes no classifier at all. So every
record carries `engine_version`, the stamp /ingest put on the proposal the
reviewer judged. It is None for a caller that had none to give, and for every
line written before this field existed.

Its shape is constrained like `corrections`: exactly five keys, each value an
identifier — letters, digits and . _ : - / only, no spaces. A digest or a
version number fits; "John Smith" doesn't.
"""

import json
import re
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


ENGINE_VERSION_FIELDS = ("model", "model_digest", "ollama_version", "kb_version", "prompt_version")

_IDENTIFIER = re.compile(r"[A-Za-z0-9._:/-]{1,100}")


def _check_engine_version(engine_version: dict | None) -> dict | None:
    if engine_version is None:
        return None
    if not isinstance(engine_version, dict) or set(engine_version) != set(ENGINE_VERSION_FIELDS):
        raise ValueError(
            f"engine_version must have exactly the fields {list(ENGINE_VERSION_FIELDS)} — "
            f"the stamp /ingest returned, passed back unchanged."
        )
    for field, value in engine_version.items():
        # None is a real answer: Ollama was down, or the model wasn't pulled.
        if value is not None and not (isinstance(value, str) and _IDENTIFIER.fullmatch(value)):
            raise ValueError(
                f"engine_version.{field} must be an identifier (letters, digits, "
                f". _ : - /), not free text — see the de-identification rule."
            )
    return {field: engine_version[field] for field in ENGINE_VERSION_FIELDS}


def log_failure(
    document_id: str,
    predicted_type: str | None,
    correct_type: str,
    note: str,
    corrections: list[dict] | None = None,
    engine_version: dict | None = None,
) -> None:
    entry = {
        "document_id": document_id,
        "predicted_type": predicted_type,
        "correct_type": correct_type,
        "note": note,
        # Always present, so a reader never has to branch on whether the key
        # exists. Empty means the document type was the only thing corrected.
        "corrections": _check_corrections(corrections or []),
        "engine_version": _check_engine_version(engine_version),
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(FAILURE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
