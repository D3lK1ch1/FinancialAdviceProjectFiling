"""
Scope gate — not a classifier. Just checks whether the parsed text contains
any title_pattern for the four document types this POC supports, reusing
knowledge_base.json so the type list isn't hardcoded here (CLAUDE.md rule #1).
No confidence score, no matched_signals, no edge_case_flags — that's the
real classifier, later.
"""

import json

IN_SCOPE_TYPES = ["soa", "roa", "fsg", "pds"]

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_TITLE_PATTERNS = {
    doc["id"]: doc["classifier_hints"]["title_patterns"]
    for doc in _KB["documents"]
    if doc["id"] in IN_SCOPE_TYPES
}


TITLE_WINDOW = 500  # documents commonly reference OTHER types by name in
                     # their body (an FSG explains what a PDS is) — scanning
                     # the whole text picks up those mentions as false
                     # positives, so only the presumed title/heading region
                     # is checked


def check_scope(text: str) -> dict:
    head = text[:TITLE_WINDOW]
    scores = {}
    for doc_id, patterns in _TITLE_PATTERNS.items():
        matched = [p for p in patterns if p in head]
        if matched:
            scores[doc_id] = sum(len(p) for p in matched)
    if not scores:
        return {"in_scope": False, "likely_type": None}
    return {"in_scope": True, "likely_type": max(scores, key=scores.get)}
