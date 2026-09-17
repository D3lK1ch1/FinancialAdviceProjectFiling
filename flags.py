"""
Flagging engine — the first rule that routes a document to human review.

Every rule lives in knowledge_base.json's `edge_case_flags` (CLAUDE.md rule
#1). This module holds the mechanics of evaluating them and nothing about what
any particular document means: the ROA's four legislative bases and the
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

_ROA_KINDS = [
    doc for doc in _KB["documents"] if doc["id"] == "roa"
][0]["legislation"]["four_kinds"]


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
    for kind in _ROA_KINDS
}

_KIND_BY_ID = {kind["id"]: kind for kind in _ROA_KINDS}


def _roa_basis_unconfirmed(doc_type: str, text: str) -> dict | None:
    """
    Which of the ROA's four bases this is. Fires on every ROA.

    That is deliberate and it is the one flag in the set that works this way.
    The others fire on an anomaly; this one fires on a property of the type.
    An ROA's basis is not recorded anywhere by classifying it as an ROA, and
    the basis is what decides the content the record must carry and whether a
    prior SOA is required at all — so there is no such thing as an ROA that
    doesn't need the question asked. advice_classification_reference.md §6
    lists exactly this against the ROA row: "Medium: confirm which of 4 bases".

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
            for kind in _ROA_KINDS
        ],
    }


# A rule is evaluated only if it appears here. Everything else in
# edge_case_flags is recorded and not yet checked, which is the honest state
# and is visible rather than implied.
EVALUATORS = {
    "roa_basis_unconfirmed": _roa_basis_unconfirmed,
}


def evaluate_flags(doc_type: str | None, text: str) -> list[dict]:
    """
    Flags for one document, from its own contents only.

    Returns a list so the shape doesn't change when the second rule lands.
    Never reclassifies and never files: a flag is a question attached to a
    proposal a human answers (CLAUDE.md rule #2).
    """
    flags = []
    for rule_id, evaluate in EVALUATORS.items():
        result = evaluate(doc_type, text)
        if result is None:
            continue
        rule = _RULES[rule_id]
        flags.append(
            {
                "id": rule_id,
                "severity": rule["severity"],
                "why": rule["why"],
                "asks": rule["asks"],
                **result,
            }
        )
    return flags
