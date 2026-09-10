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
#
# Case sensitivity is decided per pattern, by the pattern's own shape:
#
#   mixed-case patterns ("Statement of Advice")  -> case-insensitive
#   all-caps acronyms   ("SOA", "CAR")           -> case-sensitive
#
# Cover pages are routinely typeset in capitals, so a case-sensitive check
# missed "STATEMENT OF ADVICE" entirely and returned in_scope: False with no
# flag — a document silently leaving the pipeline, which is worse than a wrong
# answer because nothing surfaces for review.
#
# Casefolding the acronyms too would trade that for a new false positive: with
# word boundaries in place "CAR" no longer matches CARE or SCARBOROUGH, but a
# case-insensitive "CAR" does match the ordinary word "car" — and "car loan"
# or "car insurance" is entirely at home in the scope paragraph of an SOA. An
# acronym in a title is capitalised; the word in a sentence is not. Keying on
# `p.isupper()` uses the knowledge base's own formatting to tell them apart,
# so it stays a data decision rather than a list of exceptions in Python.
def _matcher(pattern: str) -> re.Pattern:
    flags = 0 if pattern.isupper() else re.IGNORECASE
    return re.compile(rf"\b{re.escape(pattern)}\b", flags)


_MATCHERS = {
    doc_id: [(p, _matcher(p)) for p in patterns]
    for doc_id, patterns in _TITLE_PATTERNS.items()
}


TITLE_WINDOW = 500  # documents commonly reference OTHER types by name in
                     # their body (an FSG explains what a PDS is) — scanning
                     # the whole text picks up those mentions as false
                     # positives, so only the presumed title/heading region
                     # is checked


def check_scope(text: str) -> dict:
    head = text[:TITLE_WINDOW]

    # Rank on WHERE the earliest match falls, not on how long the matching
    # pattern string is. Length was a proxy for confidence and a poor one: it
    # made "Product Disclosure Statement" (28 chars) outrank "Record of
    # Advice" (16), so an ROA that refers to the PDS of the product it
    # discusses — which is what ROAs do — came back as a pds.
    #
    # Position is the signal that was actually meant. A document's own title
    # sits at the very top; another type named further down is a
    # cross-reference. That is the same observation TITLE_WINDOW already rests
    # on, applied properly instead of approximated by string length.
    #
    # Ties break on the number of distinct patterns matched, so a type
    # supported by two hits beats one supported by a single hit at the same
    # position.
    ranking = {}
    for doc_id, matchers in _MATCHERS.items():
        positions = [found.start() for _p, pattern in matchers if (found := pattern.search(head))]
        if positions:
            ranking[doc_id] = (min(positions), -len(positions))

    if not ranking:
        return {"in_scope": False, "likely_type": None}
    return {"in_scope": True, "likely_type": min(ranking, key=ranking.get)}
