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


# Wording printed on the page that settles the type, and wording that rules a
# type out even when its title is there (Bella, 23 Oct 2026). Both live on each
# document type in the knowledge base, under `exact_phrases`.
_PHRASES = {
    doc["id"]: [_matcher(p) for p in doc.get("exact_phrases", {}).get("phrases", [])]
    for doc in _KB["documents"]
}
_RULES_OUT = {
    doc["id"]: [_matcher(p) for p in doc.get("exact_phrases", {}).get("rules_out", [])]
    for doc in _KB["documents"]
}


# How much of the top of the document counts as its title region. The value
# and the reason for it live in knowledge_base.json's `scope_gate` (#7).
TITLE_WINDOW = _KB["scope_gate"]["title_window_chars"]


def check_scope(text: str, first_page: str | None = None) -> dict:
    head = text[:TITLE_WINDOW]
    # Phrases are read across the whole first page, not only the title
    # window: "Use this form to" or "Fees and costs summary" sit below the
    # title. Without the page, fall back to the title window.
    page = head if first_page is None else first_page

    # A title is not enough on its own. Page 1 of 4 provider forms in the
    # public samples carries "Product Disclosure Statement", and page 1 of
    # every ASIC example ROA says "Statement of Advice". Form wording on the
    # page rules out a PDS; "Record of Advice" rules out an SOA.
    ruled_out = {
        doc_id for doc_id, matchers in _RULES_OUT.items()
        if any(m.search(page) for m in matchers)
    }

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
        if doc_id in ruled_out:
            continue
        positions = [found.start() for _p, pattern in matchers if (found := pattern.search(head))]
        if positions:
            ranking[doc_id] = (min(positions), -len(positions))

    if ranking:
        return {"in_scope": True, "likely_type": min(ranking, key=ranking.get)}

    # No title at the top. Many provider forms and questionnaires open on a
    # fund's letterhead or a step heading, so their title is below the window
    # or missing. The type with the most of its own phrases on page 1 wins;
    # ties go to the one found first.
    by_phrase = {}
    for doc_id, matchers in _PHRASES.items():
        if doc_id in ruled_out:
            continue
        positions = [found.start() for m in matchers if (found := m.search(page))]
        if positions:
            by_phrase[doc_id] = (-len(positions), min(positions))

    if not by_phrase:
        return {"in_scope": False, "likely_type": None}
    return {"in_scope": True, "likely_type": min(by_phrase, key=by_phrase.get)}
