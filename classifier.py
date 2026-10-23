"""
Classifier — Phase 1, per SYSTEM.md/archive/2_ARCHITECTURE.md §5: LLM returns strict
JSON {doc_type, confidence, matched_signals}, grounded by knowledge_base.json
classifier_hints (not guessed). Runs only on text scope_gate.py already
passed — this is the probabilistic step layered on top of that deterministic
pre-filter (§7), not a replacement for it.

Deliberately does NOT resolve which of the ROA's three situations applies (that's
a "confirm which kind" flag for the flagging engine, not a classifier job).
"""

import hashlib
import json

import requests

from config import OLLAMA_BASE_URL
from config import OLLAMA_MODEL as MODEL
from config import OLLAMA_TIMEOUT_SECONDS as TIMEOUT_SECONDS
from config import OLLAMA_URL
from kb import KB as _KB

_HINTS = {doc["id"]: doc["classifier_hints"] for doc in _KB["documents"]}

_DOC_TYPE_ENUM = " | ".join(f'"{doc_id}"' for doc_id in _HINTS)


def _build_prompt(text: str) -> str:
    hints_block = json.dumps(_HINTS, indent=2)
    return f"""You classify Australian financial-advice documents. You are
given classifier hints for each supported document type and the text of one
document. Respond with ONLY a JSON object, no prose, no markdown fences:

{{"doc_type": {_DOC_TYPE_ENUM}, "confidence": 0.0-1.0, "matched_signals": ["..."]}}

matched_signals must be 3-6 short quotes, each 3 to 8 words, copied
exactly from the "Document text" section below: same words, same
punctuation. Prefer headings, titles and labelled lines. Never quote the
hints, never summarise, never give a field label or category name. If you
cannot copy a phrase exactly, leave it out.

Hints (descriptions of each type, NOT text to quote):
{hints_block}

Document text (may be truncated):
{text[:6000]}
"""


# A fingerprint of everything the model is told except the document itself:
# the instructions and the hints. Editing either changes it, with nobody
# having to remember to bump a number.
PROMPT_VERSION = hashlib.sha256(_build_prompt("").encode("utf-8")).hexdigest()[:12]


def _parse_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def _full_tag(model: str) -> str:
    # Ollama lists "llama3.1" as "llama3.1:latest"; a name without a tag means latest.
    return model if ":" in model else f"{model}:latest"


def engine_identity() -> dict:
    """Exactly which model answered, as Ollama reports it right now (#7).

    The tag "llama3.1" names whatever was last pulled under it, so the next
    `ollama pull` can change every classification without any line of this
    project changing. The digest names the model's exact weights: a different
    digest is a different classifier, and the samples need re-running. Ollama
    also updated itself during the #59 experiment, so its version is recorded
    too.

    The digest comes from /api/tags. /api/show, which #7 first pointed to,
    returns no digest (checked against Ollama 0.40.6).

    Never raises. A value that can't be read is None with the reason in
    `identity_error`, because a classification that happened is still a
    classification. It is just one whose engine nobody can vouch for.
    """
    identity = {"model": MODEL, "model_digest": None, "ollama_version": None}
    errors = []
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        response.raise_for_status()
        identity["ollama_version"] = response.json().get("version")
    except (requests.RequestException, ValueError) as e:
        errors.append(f"version: {_error_text(e)}")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        wanted = _full_tag(MODEL)
        match = next((m for m in response.json().get("models", []) if _full_tag(m.get("name", "")) == wanted), None)
        if match is None:
            errors.append(f"digest: {wanted} is not pulled on this Ollama")
        else:
            identity["model_digest"] = match.get("digest")
    except (requests.RequestException, ValueError) as e:
        errors.append(f"digest: {_error_text(e)}")
    if errors:
        identity["identity_error"] = "; ".join(errors)
    return identity


def engine_version(identity: dict) -> dict:
    """The stamp for one result: which model, runtime, rules and prompt (#7).

    Everything that decides an answer besides the document. Git versions the
    rules and the prompt; the model and runtime live outside the repo, which
    is why `identity` is read from Ollama for every document rather than once
    at startup — Ollama updates itself while the app runs. Same five fields
    every time, None where a value couldn't be read.
    """
    return {
        "model": identity["model"],
        "model_digest": identity["model_digest"],
        "ollama_version": identity["ollama_version"],
        "kb_version": _KB["meta"]["version"],
        "prompt_version": PROMPT_VERSION,
    }


def _error_text(e: Exception) -> str:
    """The exception, plus Ollama's own explanation when it sent one.

    On an HTTP error, str(e) is only "404 Client Error: Not Found for url ...".
    The reason a person can act on — "model 'llama3.2' not found, try pulling
    it first" — is in the response body's `error` field, and was discarded.
    """
    response = getattr(e, "response", None)
    if response is not None:
        try:
            detail = response.json().get("error")
        except ValueError:
            detail = None
        if detail:
            return f"{e} — Ollama says: {detail}"
    return str(e)


def classify(text: str) -> dict:
    prompt = _build_prompt(text)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        raw = response.json()["response"]
        parsed = _parse_response(raw)
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        return {
            "doc_type": None,
            "confidence": 0.0,
            "matched_signals": [],
            "classifier_error": _error_text(e),
        }

    return {
        "doc_type": parsed.get("doc_type"),
        "confidence": parsed.get("confidence", 0.0),
        "matched_signals": parsed.get("matched_signals", []),
    }
