"""
Scope gate — not a classifier. Just checks whether the parsed text contains
any title_pattern for the four document types this POC supports, reusing
knowledge_base.json so the type list isn't hardcoded here (CLAUDE.md rule #1).
No confidence score, no matched_signals, no edge_case_flags — that's the
real classifier, later.
"""

import json
import re

IN_SCOPE_TYPES = ["soa", "roa", "fsg", "pds"]

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_TITLE_PATTERNS = {
    doc["id"]: doc["classifier_hints"]["title_patterns"]
    for doc in _KB["documents"]
    if doc["id"] in IN_SCOPE_TYPES
}

# Patterns match on word boundaries, not as bare substrings. Six of the KB's
# title_patterns are three-letter acronyms, and `"ROA" in head` is also true
# for ROAD and BROADWAY. Every advice document carries a letterhead with a
# street address, and it sits inside exactly the first 500 chars this function
# reads — so a document issued from "42 BROADWAY" scored as an ROA. That is a
# live misclassification on ordinary documents, not a contrived one.
_MATCHERS = {
    doc_id: [(p, re.compile(rf"\b{re.escape(p)}\b")) for p in patterns]
    for doc_id, patterns in _TITLE_PATTERNS.items()
}


TITLE_WINDOW = 500  # documents commonly reference OTHER types by name in
                     # their body (an FSG explains what a PDS is) — scanning
                     # the whole text picks up those mentions as false
                     # positives, so only the presumed title/heading region
                     # is checked


def check_scope(text: str) -> dict:
    head = text[:TITLE_WINDOW]
    scores = {}
    for doc_id, matchers in _MATCHERS.items():
        matched = [p for p, pattern in matchers if pattern.search(head)]
        if matched:
            scores[doc_id] = sum(len(p) for p in matched)
    if not scores:
        return {"in_scope": False, "likely_type": None}
    return {"in_scope": True, "likely_type": max(scores, key=scores.get)}
