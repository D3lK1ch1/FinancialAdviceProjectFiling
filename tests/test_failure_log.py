"""Unit tests for failure_log.py — log_failure() appends correctly-shaped
JSON Lines records. Uses monkeypatch + tmp_path so tests never touch the
real failure_log.jsonl.
"""

import json

from failure_log import log_failure


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
