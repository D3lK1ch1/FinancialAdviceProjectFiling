"""Unit tests for failure_log.py — log_failure() appends correctly-shaped
JSON Lines records. Uses monkeypatch + tmp_path so tests never touch the
real failure_log.jsonl.
"""

import json
from datetime import datetime, timedelta

from failure_log import log_failure

# failure_log.jsonl is committed to git and shared between collaborators, so —
# unlike samples/ — it travels, and the record has to stay de-identified. The
# rule itself is in failure_log.py's docstring and README's Failure log section.
#
# Asserting the EXACT field set, rather than "these keys are present", is what
# makes this a guard instead of a description: adding a client_name, adviser or
# balance field to log_failure() fails this test first and forces the
# conversation before any client identity can reach a shared file.
DEIDENTIFIED_FIELDS = {
    "document_id",
    "predicted_type",
    "correct_type",
    "note",
    "logged_at",
}


def test_log_failure_appends_json_line(tmp_path, monkeypatch):
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("SOA_RG90_scaled_advice.pdf", "roa", "soa", "misread SOA disclosure as ROA")

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["document_id"] == "SOA_RG90_scaled_advice.pdf"
    assert entry["predicted_type"] == "roa"
    assert entry["correct_type"] == "soa"
    assert entry["note"] == "misread SOA disclosure as ROA"
    assert "logged_at" in entry


def test_log_failure_handles_none_predicted_type(tmp_path, monkeypatch):
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("blank.pdf", None, "soa", "classifier_error: timed out")

    entry = json.loads(log_path.read_text().strip())
    assert entry["predicted_type"] is None
    assert entry["note"] == "classifier_error: timed out"


def test_log_failure_appends_without_overwriting(tmp_path, monkeypatch):
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("a.pdf", "fsg", "pds", "note a")
    log_failure("b.pdf", "pds", "fsg", "note b")

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["document_id"] == "a.pdf"
    assert json.loads(lines[1])["document_id"] == "b.pdf"


def test_log_failure_record_carries_only_deidentified_fields(tmp_path, monkeypatch):
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("SOA_RG90_scaled_advice.pdf", "roa", "soa", "misread SOA disclosure as ROA")

    entry = json.loads(log_path.read_text().strip())
    assert set(entry) == DEIDENTIFIED_FIELDS, (
        "The failure_log.jsonl record shape changed. This file is committed and "
        "shared, so every field in it must be de-identified — see the rule in "
        "failure_log.py. If a record needs more context, add a reference someone "
        "with access can look up, not the content itself."
    )


def test_log_failure_logged_at_is_utc_iso8601(tmp_path, monkeypatch):
    # Part of the record's shape, and load-bearing for the move to the SQLite
    # failure_log table later: a naive local timestamp is not comparable across
    # two collaborators in different places.
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("blank.pdf", None, "soa", "classifier_error: timed out")

    entry = json.loads(log_path.read_text().strip())
    logged_at = datetime.fromisoformat(entry["logged_at"])
    assert logged_at.tzinfo is not None, "logged_at must carry a timezone, not be naive"
    assert logged_at.utcoffset() == timedelta(0), "logged_at must be UTC"
