"""
Classifier — Phase 1, per SYSTEM.md/2_ARCHITECTURE.md §5: LLM returns strict
JSON {doc_type, confidence, matched_signals}, grounded by knowledge_base.json
classifier_hints (not guessed). Runs only on text scope_gate.py already
passed — this is the probabilistic step layered on top of that deterministic
pre-filter (§7), not a replacement for it.

Deliberately does NOT resolve ROA's four legislative bases (CLAUDE.md: that's
a "confirm which kind" flag for the flagging engine, not a classifier job).
"""

import json

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_HINTS = {doc["id"]: doc["classifier_hints"] for doc in _KB["documents"]}

_DOC_TYPE_ENUM = " | ".join(f'"{doc_id}"' for doc_id in _HINTS)


def _build_prompt(text: str) -> str:
    hints_block = json.dumps(_HINTS, indent=2)
    return f"""You classify Australian financial-advice documents. You are
given classifier hints for each supported document type and the text of one
document. Respond with ONLY a JSON object, no prose, no markdown fences:

{{"doc_type": {_DOC_TYPE_ENUM}, "confidence": 0.0-1.0, "matched_signals": ["..."]}}

matched_signals must be short phrases actually present in the document text
that support your answer (e.g. a title phrase, a key field you found).

Classifier hints:
{hints_block}

Document text (may be truncated):
{text[:6000]}
"""


def _parse_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def classify(text: str) -> dict:
    prompt = _build_prompt(text)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=180,
        )
        response.raise_for_status()
        raw = response.json()["response"]
        parsed = _parse_response(raw)
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        return {
            "doc_type": None,
            "confidence": 0.0,
            "matched_signals": [],
            "classifier_error": str(e),
        }

    return {
        "doc_type": parsed.get("doc_type"),
        "confidence": parsed.get("confidence", 0.0),
        "matched_signals": parsed.get("matched_signals", []),
    }
