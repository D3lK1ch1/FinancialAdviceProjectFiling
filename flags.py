"""
Flagging engine — the first rule that routes a document to human review.

Every rule lives in knowledge_base.json's `edge_case_flags` (CLAUDE.md rule
#1). This module holds the mechanics of evaluating them and nothing about what
any particular document means: the three situations permitting an ROA and the
phrases that indicate each are data in the knowledge base, and adding a fifth
basis — or correcting a signal that misfires on real files — is an edit there,
not here.

Only rules declared `"evaluation": "stateless"` can be evaluated at ingest.
The stateful ones need other documents for the same client on record, which
nothing persists yet (#8). A rule is run only if this module registers an
evaluator for it, and a test asserts every registered evaluator belongs to a
rule the knowledge base declares stateless — so the engine can never report
having checked something it had no evidence for.
"""

import json
import re

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_RULES = {rule["id"]: rule for rule in _KB["edge_case_flags"]["rules"]}

_ROA_SITUATIONS = [
    doc for doc in _KB["documents"] if doc["id"] == "roa"
][0]["legislation"]["situations"]

_BUNDLE = _RULES["multi_doc_bundle"]["detection"]
_PAGINATION = re.compile(_BUNDLE["pagination_restart"]["pattern"], re.IGNORECASE)
_LEADING = _BUNDLE["leading_region_chars"]


# Signals are body phrases, not title acronyms, so all of them match
# case-insensitively — unlike scope_gate.py, which keeps all-caps patterns
# case-sensitive to stop "CAR" matching the ordinary word. Nothing here is a
# bare short word, so that trade-off doesn't arise.
#
# The boundaries are lookarounds rather than \b because several signals start
# or end on a non-word character ("reg 7.7.09A", "s946AA"), and \b next to one
# of those asserts the opposite of what's wanted. Lookarounds behave the same
# whatever the phrase's edges are.
def _matcher(phrase: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE)


_KIND_MATCHERS = {
    kind["id"]: {
        strength: [(phrase, _matcher(phrase)) for phrase in phrases]
        for strength, phrases in kind["basis_signals"].items()
    }
    for kind in _ROA_SITUATIONS
}

_KIND_BY_ID = {kind["id"]: kind for kind in _ROA_SITUATIONS}


def _roa_basis_unconfirmed(doc_type: str, text: str) -> dict | None:
    """
    Which of the ROA's three situations this is. Fires on every ROA.

    That is deliberate and it is the one flag in the set that works this way.
    The others fire on an anomaly; this one fires on a property of the type.
    An ROA's basis is not recorded anywhere by classifying it as an ROA, and
    the basis is what decides the content the record must carry and whether a
    prior SOA is required at all — so there is no such thing as an ROA that
    doesn't need the question asked.

    THREE situations, not four: s946B(7) is the no-buy/sell provision and reg
    7.7.10AAA substitutes a notional version of it, so carrying them
    separately counted one situation twice. "Hold" is what the advice
    recommends, not why an ROA is allowed. Decided on issue #33.

    What varies is how much of the answer the flag can offer. Where the text
    supports exactly one basis it proposes it and cites the phrases it
    matched, so the reviewer confirms or corrects one thing instead of
    starting from scratch. Where it supports several, or none, it says so and
    proposes nothing — an honest "which kind is this?" is worth more than a
    guess, because a wrong basis recorded confidently is harder to catch later
    than an open question.
    """
    if doc_type != "roa":
        return None

    def _matched(strength: str) -> dict:
        return {
            kind_id: hits
            for kind_id, by_strength in _KIND_MATCHERS.items()
            if (hits := [p for p, rx in by_strength[strength] if rx.search(text)])
        }

    # A document that names the situation it was written under outranks a
    # basis read off the shape of the recommendation. INFO 266 attachment 1 is
    # the case that settles it: it says "This ROA contains further advice",
    # and it also says "My advice is to make no changes to your XYZ
    # Superannuation Fund" while increasing the client's insurance cover. Both
    # sentences are the document's own. Weighing them equally makes the most
    # canonical further-advice example in the public set read as ambiguous;
    # letting the declaration win reads it correctly. See the ROA entry's
    # calibration_note.
    evidence = _matched("declared") or _matched("inferred")

    if len(evidence) == 1:
        kind_id, matched = next(iter(evidence.items()))
        kind = _KIND_BY_ID[kind_id]
        return {
            "determination": "proposed",
            "proposed_basis": kind_id,
            "proposed_basis_name": kind["kind"],
            "proposed_basis_provision": kind["basis"],
            "matched_signals": matched,
        }

    return {
        "determination": "ambiguous" if evidence else "absent",
        "proposed_basis": None,
        "candidates": [
            {
                "basis": kind_id,
                "name": _KIND_BY_ID[kind_id]["kind"],
                "provision": _KIND_BY_ID[kind_id]["basis"],
                "matched_signals": matched,
            }
            for kind_id, matched in evidence.items()
        ]
        or [
            {
                "basis": kind["id"],
                "name": kind["kind"],
                "provision": kind["basis"],
                "matched_signals": [],
            }
            for kind in _ROA_SITUATIONS
        ],
    }




def _page_types(pages: list[str]) -> list[str | None]:
    """The type each page's leading region reads as, by the scope gate's own
    title patterns — imported rather than re-derived, so a knowledge-base edit
    moves both together.
    """
    from scope_gate import _MATCHERS  # noqa: PLC0415 — same KB data, one source

    types = []
    for page in pages:
        head = page[:_LEADING]
        best = None
        for doc_id, matchers in _MATCHERS.items():
            positions = [f.start() for _p, rx in matchers if (f := rx.search(head))]
            if positions:
                candidate = (min(positions), -len(positions), doc_id)
                if best is None or candidate < best:
                    best = candidate
        types.append(best[2] if best else None)
    return types


def _pagination_restarts(pages: list[str]) -> list[dict]:
    """Pages where a document's own numbering starts over.

    The strong signal, and the one that needs no notion of type at all: "page
    1 of N" on page 31 of a 53-page file says a second document begins there
    whatever either document is about.
    """
    found = []
    for number, page in enumerate(pages, start=1):
        if number == 1:
            continue
        for match in _PAGINATION.finditer(page):
            if match.group(1) == "1":
                found.append({"page": number, "marker": " ".join(match.group(0).split())})
                break
    return found


def _title_transitions(pages: list[str]) -> list[dict]:
    """Pages where the type implied by the heading changes and does not change back.

    A running header gives the same type on every page, so presence of a
    second type's name is not the signal — the CHANGE is. And a change that
    hands the file back to the earlier type was a section inside one document,
    not an appended one: that is what separates a PDS with a "risk profile"
    section from a PDS with something genuinely stapled to it.
    """
    seen = [(number, t) for number, t in enumerate(_page_types(pages), start=1) if t]

    transitions = []
    for index in range(1, len(seen)):
        page, doc_type = seen[index]
        previous = seen[index - 1][1]
        if doc_type == previous:
            continue
        if previous in {t for _n, t in seen[index:]}:
            continue  # the earlier type comes back: an excursion, not a boundary
        if doc_type in {t for _n, t in seen[:index]}:
            continue  # and the file handing itself back to a type it already
            # was is the end of that excursion, not the start of a document
        transitions.append({"page": page, "from": previous, "to": doc_type})
    return transitions


def _multi_doc_bundle(doc_type: str, text: str, pages: list[str] | None) -> dict | None:
    """Whether this file looks like more than one document.

    Needs page boundaries, which is why #21 had to land first: joined text
    cannot show where one document ends and the next begins.

    It proposes candidates and never splits. A missed bundle is a flag nobody
    actioned; a wrong split cuts a record in half and nothing downstream can
    tell that it happened.
    """
    if not pages or len(pages) < 2:
        return None

    restarts = _pagination_restarts(pages)
    transitions = _title_transitions(pages)
    if not restarts and not transitions:
        return None

    candidates = sorted(
        [{"page": r["page"], "evidence": "pagination_restart", "detail": r["marker"],
          "strength": _BUNDLE["pagination_restart"]["strength"]} for r in restarts]
        + [{"page": t["page"], "evidence": "title_transition",
            "detail": f'{t["from"]} -> {t["to"]}',
            "strength": _BUNDLE["title_transition"]["strength"]} for t in transitions],
        key=lambda c: (c["page"], c["evidence"]),
    )

    return {
        "page_count": len(pages),
        "candidate_boundaries": candidates,
        "proposed_split": [
            {"from_page": start, "to_page": end}
            for start, end in zip(
                [1] + [c["page"] for c in candidates],
                [c["page"] - 1 for c in candidates] + [len(pages)],
            )
        ],
        "split_performed": False,
        "never_split_automatically": _RULES["multi_doc_bundle"]["never_split_automatically"],
    }

# A rule is evaluated only if it appears here. Everything else in
# edge_case_flags is recorded and not yet checked, which is the honest state
# and is visible rather than implied.
EVALUATORS = {
    "roa_basis_unconfirmed": _roa_basis_unconfirmed,
    "multi_doc_bundle": _multi_doc_bundle,
}


_NEEDS_PAGES = {"multi_doc_bundle"}


def evaluate_flags(doc_type: str | None, text: str, pages: list[str] | None = None) -> list[dict]:
    """
    Flags for one document, from its own contents only.

    `pages` is per-page text from parse_pdf. Bundle detection needs it —
    joined text cannot show where one document ends and the next begins — and
    rules that do not care about page structure ignore it.
    Never reclassifies and never files: a flag is a question attached to a
    proposal a human answers (CLAUDE.md rule #2).
    """
    flags = []
    for rule_id, evaluate in EVALUATORS.items():
        result = (
            evaluate(doc_type, text, pages)
            if rule_id in _NEEDS_PAGES
            else evaluate(doc_type, text)
        )
        if result is None:
            continue
        rule = _RULES[rule_id]
        flags.append(
            {
                "id": rule_id,
                "severity": rule["severity"],
                "forces_review": rule.get("forces_review"),
                "why": rule["why"],
                "asks": rule["asks"],
                **result,
            }
        )
    return flags
