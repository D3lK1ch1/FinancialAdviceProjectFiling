"""Unit tests for classifier.py — _parse_response() and classify(), mocked.

No live Ollama here: requests.post is patched so these run offline and
deterministically. The real-Ollama path is covered separately by the e2e
test, which hits it for real.
"""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from classifier import _build_prompt, _parse_response, classify

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


# --- _build_prompt (#59) ---------------------------------------------------
# confidence.py marks down every quote it can't find in the document, so what
# the prompt asks for decides whether correct answers reach review. These pin
# the parts measured in docs/EXPERIMENT_LOG.md.


def _flat(text: str) -> str:
    # The prompt wraps lines; compare wording, not where the line breaks fall.
    return " ".join(text.split())


def test_prompt_asks_for_exact_quotes_not_summaries_or_labels():
    prompt = _flat(_build_prompt("some document text"))

    assert 'copied exactly from the "Document text" section' in prompt
    assert "never summarise" in prompt
    assert "never give a field label" in prompt


def test_prompt_puts_document_text_last():
    prompt = _build_prompt("UNIQUE-DOC-MARKER")

    assert prompt.index("Hints (") < prompt.index("UNIQUE-DOC-MARKER")
    assert prompt.rstrip().endswith("UNIQUE-DOC-MARKER")


@patch("classifier.requests.post")
def test_classify_sends_temperature_zero_as_a_number(mock_post):
    mock_post.return_value = _mock_ollama_response(VALID_JSON)

    classify("some document text")

    options = mock_post.call_args.kwargs["json"]["options"]
    assert options["temperature"] == 0
    # Ollama rejects "0" (a string) with a 500, and ignores a misspelled key.
    assert not isinstance(options["temperature"], str)
