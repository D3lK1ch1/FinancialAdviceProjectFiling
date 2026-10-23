"""
Scope gate — not a classifier. Just checks whether the parsed text contains
any title_pattern for the document types knowledge_base.json defines, reading
the list from there so it isn't hardcoded here (CLAUDE.md rule #1).
No confidence score, no matched_signals, no edge_case_flags — that's the
real classifier, later.
"""

import re

from kb import KB as _KB

# The supported set is whatever the knowledge base defines — never a list in
# Python (CLAUDE.md rule #1). Previously this was hardcoded to four types in
# three separate files while the KB defined nine, so the five it didn't know
# about left the pipeline as in_scope: False with no type and no flag —
# indistinguishable from an unreadable file.
IN_SCOPE_TYPES = [doc["id"] for doc in _KB["documents"]]

_TITLE_PATTERNS = {
    doc["id"]: doc["classifier_hints"]["title_patterns"]
    for doc in _KB["documents"]
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
# Any run of whitespace between a title's words counts as one space. PDF
# extraction often breaks a title across lines: ASIC's own RG 90 example SOA
# reads "Statement of\nAdvice", so an exact single-space match left both ASIC
# SOAs out of scope and the model never saw them.
def _matcher(pattern: str) -> re.Pattern:
    flags = 0 if pattern.isupper() else re.IGNORECASE
    words = r"\s+".join(re.escape(w) for w in pattern.split())
    return re.compile(rf"\b{words}\b", flags)


_MATCHERS = {
    doc_id: [(p, _matcher(p)) for p in patterns]
    for doc_id, patterns in _TITLE_PATTERNS.items()
}


# How much of the top of the document counts as its title region. The value
# and the reason for it live in knowledge_base.json's `scope_gate` (#7).
TITLE_WINDOW = _KB["scope_gate"]["title_window_chars"]


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
