"""Unit tests for failure_log.py — log_failure() appends correctly-shaped
JSON Lines records. Uses monkeypatch + tmp_path so tests never touch the
real failure_log.jsonl.
"""

import json
from datetime import datetime, timedelta

import pytest

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
    "corrections",
    "logged_at",
}

# The same guard one level down. `corrections` is the extension point for
# every future flag, which makes it the place a client name would eventually
# be written by somebody being helpful. It has no free-text field, and this
# asserts that it never gains one.
CORRECTION_FIELDS = {"kind", "predicted", "correct"}


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



# --- #12: corrections beyond the document type ---

def test_a_corrected_roa_situation_can_be_recorded(tmp_path, monkeypatch):
    """The gap this was raised for. predicted_type/correct_type record that
    the tool said PDS and it was a file note. A reviewer correcting
    further_advice to no_buy_sell is the same weight of correction about the
    same document, and had nowhere to go.
    """
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure(
        "roa_2025_03.pdf", "roa", "roa", "type right, situation wrong",
        corrections=[{"kind": "roa_situation",
                      "predicted": "further_advice", "correct": "no_buy_sell"}],
    )

    entry = json.loads(log_path.read_text().strip())
    assert entry["corrections"] == [
        {"kind": "roa_situation", "predicted": "further_advice", "correct": "no_buy_sell"}
    ]


def test_more_than_one_thing_can_be_corrected_at_once(tmp_path, monkeypatch):
    """A reviewer looking at one document can disagree about several things,
    and a second field pair per kind would mean a schema change for every
    future flag.
    """
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure(
        "scan_014.pdf", "pds", "file_note", "meeting note read as a PDS",
        corrections=[
            {"kind": "doc_type", "predicted": "pds", "correct": "file_note"},
            {"kind": "confidence", "predicted": 0.82, "correct": 0.2},
        ],
    )

    entry = json.loads(log_path.read_text().strip())
    assert [c["kind"] for c in entry["corrections"]] == ["doc_type", "confidence"]


def test_corrections_is_always_present_even_when_empty(tmp_path, monkeypatch):
    """So a reader never branches on whether the key exists."""
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("a.pdf", "fsg", "pds", "note a")

    assert json.loads(log_path.read_text().strip())["corrections"] == []


def test_an_unknown_correction_kind_is_refused(tmp_path, monkeypatch):
    """A log that silently accepts anything stops being evidence of anything.
    Adding a kind is a deliberate act, not something a caller can invent.
    """
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    with pytest.raises(ValueError, match="unknown correction kind"):
        log_failure("a.pdf", "fsg", "pds", "note",
                    corrections=[{"kind": "adviser_name",
                                  "predicted": "x", "correct": "y"}])

    assert not log_path.exists(), "nothing may be written when a kind is refused"


def test_a_correction_cannot_carry_a_free_text_field(tmp_path, monkeypatch):
    """The de-identification rule expressed as a shape. `corrections` is the
    extension point every future flag will use, which makes it exactly where a
    client name would eventually be written by somebody being helpful at the
    end of the day. There is nowhere for it to go.
    """
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    with pytest.raises(ValueError, match="unexpected field"):
        log_failure("a.pdf", "roa", "roa", "note",
                    corrections=[{"kind": "roa_situation", "predicted": "further_advice",
                                  "correct": "no_buy_sell",
                                  "note": "confirmed with Linh Nguyen on the phone"}])

    assert not log_path.exists()


def test_each_correction_carries_only_deidentified_fields(tmp_path, monkeypatch):
    """The record-shape guard, one level down. Asserting the EXACT field set
    is what makes it a guard rather than a description.
    """
    log_path = tmp_path / "failure_log.jsonl"
    monkeypatch.setattr("failure_log.FAILURE_LOG_PATH", log_path)

    log_failure("a.pdf", "roa", "roa", "note",
                corrections=[{"kind": "roa_situation",
                              "predicted": "further_advice", "correct": "no_buy_sell"}])

    entry = json.loads(log_path.read_text().strip())
    for correction in entry["corrections"]:
        assert set(correction) == CORRECTION_FIELDS, (
            "A correction record grew a field. This file is committed and shared, "
            "so every field in it must be de-identified — see failure_log.py. "
            "Record a knowledge-base category, never text out of a document."
        )


def test_every_known_kind_explains_itself():
    """So the vocabulary stays readable rather than becoming three opaque
    strings nobody can extend confidently.
    """
    from failure_log import CORRECTION_KINDS

    assert CORRECTION_KINDS
    for kind, description in CORRECTION_KINDS.items():
        assert kind.islower() and description.strip(), kind
