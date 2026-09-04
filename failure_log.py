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

No review UI exists yet to capture human corrections (unit #12), so the
current caller is tests/test_e2e.py: it has both a real classifier
prediction and a hand-labelled correct answer for every sample, which is
exactly the comparison this log exists to record.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

FAILURE_LOG_PATH = Path(__file__).resolve().parent / "failure_log.jsonl"


def log_failure(document_id: str, predicted_type: str | None, correct_type: str, note: str) -> None:
    entry = {
        "document_id": document_id,
        "predicted_type": predicted_type,
        "correct_type": correct_type,
        "note": note,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(FAILURE_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
