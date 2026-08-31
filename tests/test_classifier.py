"""Unit tests for classifier.py — _parse_response() and classify(), mocked.

No live Ollama here: requests.post is patched so these run offline and
deterministically. The real-Ollama path is covered separately by the e2e
test, which hits it for real.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from classifier import _parse_response, classify

VALID_JSON = '{"doc_type": "soa", "confidence": 0.92, "matched_signals": ["Statement of Advice"]}'


# --- _parse_response ---------------------------------------------------


def test_parse_response_plain_json():
    result = _parse_response(VALID_JSON)
    assert result == {
        "doc_type": "soa",
        "confidence": 0.92,
        "matched_signals": ["Statement of Advice"],
    }


def test_parse_response_fenced_with_json_tag():
    raw = f"```json\n{VALID_JSON}\n```"
    assert _parse_response(raw) == json.loads(VALID_JSON)


def test_parse_response_fenced_without_language_tag():
    raw = f"```\n{VALID_JSON}\n```"
    assert _parse_response(raw) == json.loads(VALID_JSON)


def test_parse_response_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_response("not json at all")


# --- classify() ----------------------------------------------------------


def _mock_ollama_response(response_text: str) -> Mock:
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"response": response_text}
    return mock_response


@patch("classifier.requests.post")
def test_classify_success(mock_post):
    mock_post.return_value = _mock_ollama_response(VALID_JSON)

    result = classify("some document text")

    assert result == {
        "doc_type": "soa",
        "confidence": 0.92,
        "matched_signals": ["Statement of Advice"],
    }
    assert "classifier_error" not in result


@patch("classifier.requests.post")
def test_classify_missing_optional_fields_default(mock_post):
    mock_post.return_value = _mock_ollama_response('{"doc_type": "fsg"}')

    result = classify("some document text")

    assert result == {"doc_type": "fsg", "confidence": 0.0, "matched_signals": []}


@patch("classifier.requests.post")
def test_classify_request_exception_returns_fallback(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError("Ollama not reachable")

    result = classify("some document text")

    assert result["doc_type"] is None
    assert result["confidence"] == 0.0
    assert result["matched_signals"] == []
    assert "Ollama not reachable" in result["classifier_error"]


@patch("classifier.requests.post")
def test_classify_malformed_json_returns_fallback(mock_post):
    mock_post.return_value = _mock_ollama_response("not valid json")

    result = classify("some document text")

    assert result["doc_type"] is None
    assert result["confidence"] == 0.0
    assert result["matched_signals"] == []
    assert "classifier_error" in result


@patch("classifier.requests.post")
def test_classify_missing_response_key_returns_fallback(mock_post):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {}  # no "response" key
    mock_post.return_value = mock_response

    result = classify("some document text")

    assert result["doc_type"] is None
    assert "classifier_error" in result
