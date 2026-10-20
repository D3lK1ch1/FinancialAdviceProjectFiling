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


# --- Connection settings and error text (#7) -------------------------------


@patch("classifier.requests.post")
def test_classify_keeps_ollamas_own_error_message(mock_post):
    # What Ollama returns for a model that was never pulled: a 404 whose body
    # says why. The status line alone tells a reviewer nothing to act on.
    body = Mock()
    body.json.return_value = {"error": "model 'llama3.2' not found, try pulling it first"}
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Client Error: Not Found", response=body
    )
    mock_post.return_value = mock_response

    result = classify("some document text")

    assert "404 Client Error" in result["classifier_error"]
    assert "model 'llama3.2' not found" in result["classifier_error"]


@patch("classifier.requests.post")
def test_classify_error_without_a_body_is_unchanged(mock_post):
    body = Mock()
    body.json.side_effect = ValueError("no JSON body")
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Server Error", response=body
    )
    mock_post.return_value = mock_response

    assert classify("some document text")["classifier_error"] == "500 Server Error"


def test_connection_settings_default_to_the_values_the_project_runs_with(monkeypatch):
    import importlib

    import classifier
    import config

    for name in ("OLLAMA_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    try:
        importlib.reload(config)
        reloaded = importlib.reload(classifier)
        assert reloaded.OLLAMA_URL == "http://localhost:11434/api/generate"
        assert reloaded.MODEL == "llama3.1"
        assert reloaded.TIMEOUT_SECONDS == 180
    finally:
        monkeypatch.undo()
        importlib.reload(config)
        importlib.reload(classifier)


@patch("requests.post")
def test_connection_settings_come_from_the_environment(mock_post, monkeypatch):
    import importlib

    import classifier
    import config

    monkeypatch.setenv("OLLAMA_URL", "http://other-host:11434/api/generate")
    monkeypatch.setenv("OLLAMA_MODEL", "some-model")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "30")
    mock_post.return_value = _mock_ollama_response(VALID_JSON)
    try:
        importlib.reload(config)
        reloaded = importlib.reload(classifier)
        reloaded.classify("some document text")

        assert mock_post.call_args.args[0] == "http://other-host:11434/api/generate"
        assert mock_post.call_args.kwargs["json"]["model"] == "some-model"
        assert mock_post.call_args.kwargs["timeout"] == 30
    finally:
        monkeypatch.undo()
        importlib.reload(config)
        importlib.reload(classifier)


# --- engine_identity (#7) -----------------------------------------------------
# Which exact model answered. Ollama's real shapes: /api/version returns
# {"version": ...}; /api/tags lists pulled models with their digests.

_TAGS = {"models": [
    {"name": "qwen2.5:3b", "digest": "357c53fb"},
    {"name": "llama3.1:latest", "digest": "46e0c10c"},
]}


def _get_returning(version=None, tags=None, fail=None):
    def fake_get(url, timeout):
        if fail and fail in url:
            raise requests.exceptions.ConnectionError("refused")
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = version if url.endswith("/api/version") else tags
        return response
    return fake_get


@patch("classifier.requests.get")
def test_engine_identity_reads_the_digest_of_the_model_in_use(mock_get):
    from classifier import engine_identity

    mock_get.side_effect = _get_returning({"version": "0.40.6"}, _TAGS)

    assert engine_identity() == {
        "model": "llama3.1",
        "model_digest": "46e0c10c",  # "llama3.1" is listed as "llama3.1:latest"
        "ollama_version": "0.40.6",
    }


@patch("classifier.requests.get")
def test_engine_identity_says_so_when_the_model_is_not_pulled(mock_get):
    from classifier import engine_identity

    mock_get.side_effect = _get_returning({"version": "0.40.6"}, {"models": [_TAGS["models"][0]]})

    identity = engine_identity()

    assert identity["model_digest"] is None
    assert identity["ollama_version"] == "0.40.6"
    assert "llama3.1:latest is not pulled" in identity["identity_error"]


@patch("classifier.requests.get")
def test_engine_identity_never_raises_when_ollama_is_down(mock_get):
    from classifier import engine_identity

    mock_get.side_effect = _get_returning(fail="/api/")

    identity = engine_identity()

    assert identity["model"] == "llama3.1"
    assert identity["model_digest"] is None
    assert identity["ollama_version"] is None
    assert "version: refused" in identity["identity_error"]
    assert "digest: refused" in identity["identity_error"]


@patch("classifier.requests.get")
def test_engine_identity_asks_the_same_server_classify_uses(mock_get):
    from classifier import engine_identity

    mock_get.side_effect = _get_returning({"version": "0.40.6"}, _TAGS)

    engine_identity()

    asked = {call.args[0] for call in mock_get.call_args_list}
    assert asked == {"http://localhost:11434/api/version", "http://localhost:11434/api/tags"}
