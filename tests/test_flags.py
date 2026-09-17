"""Unit tests for flags.py — the roa_basis_unconfirmed rule.

All plain text, no `samples/` needed, so they run on a bare clone.

The ROA texts here are written to the four bases described in
knowledge_base.json and advice_classification_reference.md §4, not copied from
the sample set: the public sample set covers three of the four (INFO 266 att 1
further advice, att 2 no-action, att 3 small-investment flavour) and has no
no-buy/sell example at all, so a fourth case has to be written to be tested.
"""

import json

import pytest

from flags import EVALUATORS, evaluate_flags

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_RULES = {rule["id"]: rule for rule in _KB["edge_case_flags"]["rules"]}


def _roa_flag(text):
    flags = [f for f in evaluate_flags("roa", text) if f["id"] == "roa_basis_unconfirmed"]
    assert len(flags) == 1, "the rule fires exactly once per ROA"
    return flags[0]


# One text per legislative basis, each stating its basis the way a real record
# of that kind does.
BASES = [
    (
        "further_advice",
        "Record of Advice. Client: L & D Nguyen. Further advice referencing the "
        "prior Statement of Advice dated 14 March 2024. Recommendation: increase "
        "life cover following the birth of a child. No material change in the "
        "basis of advice. Date: 10 September 2025.",
    ),
    (
        "hold_no_action",
        "Record of Advice. Client: A Patel. We have reviewed your portfolio "
        "against your objectives and recommend you take no action at this time. "
        "You remain invested in your current options. Date: 2 February 2025.",
    ),
    (
        "small_investment",
        "Record of Advice. Client: M Okafor. This is small investment advice "
        "provided under s946AA, with content and timing per reg 7.7.09A. "
        "Date: 8 August 2025.",
    ),
    (
        "no_buy_sell",
        "Record of Advice. Client: S Tran. This advice contains no recommendation "
        "to acquire or dispose of a financial product, and is given under "
        "reg 7.7.10AAA. Date: 19 June 2025.",
    ),
]


@pytest.mark.parametrize("expected_basis, text", BASES, ids=[b for b, _ in BASES])
def test_each_basis_is_proposed_with_its_evidence(expected_basis, text):
    """Where the text supports exactly one basis, the flag names it and cites
    the phrases it matched — so the reviewer confirms one thing rather than
    being handed the whole question back (#20's 'show the decision and its
    reason' note).
    """
    flag = _roa_flag(text)

    assert flag["determination"] == "proposed"
    assert flag["proposed_basis"] == expected_basis
    assert flag["matched_signals"], "a proposed basis must cite its evidence"
    for phrase in flag["matched_signals"]:
        assert phrase.lower() in text.lower(), f"{phrase!r} was not in the document"


def test_no_basis_signal_proposes_nothing_and_says_so():
    """The honest default. An ROA that never states its basis is common, and
    an open 'which kind is this?' is worth more than a guess: a wrong basis
    recorded confidently is harder to catch later than an unanswered question.
    """
    flag = _roa_flag(
        "Record of Advice. Client: A Patel. We discussed your superannuation "
        "and your stated goals. Date: 1 July 2025."
    )

    assert flag["determination"] == "absent"
    assert flag["proposed_basis"] is None
    assert len(flag["candidates"]) == 4, "all four bases stay open"
    assert all(c["matched_signals"] == [] for c in flag["candidates"])


def test_two_declared_bases_list_both_rather_than_picking():
    """A record that declares itself further advice AND small investment
    advice is exactly the case a human should settle. Picking one on a
    tie-break would be inventing certainty the document doesn't carry.
    """
    flag = _roa_flag(
        "Record of Advice. This contains further advice following our earlier "
        "meeting, and is given as small investment advice."
    )

    assert flag["determination"] == "ambiguous"
    assert flag["proposed_basis"] is None
    assert {c["basis"] for c in flag["candidates"]} == {"further_advice", "small_investment"}


def test_a_declared_basis_beats_a_basis_inferred_from_the_recommendation():
    """The INFO 266 attachment 1 case, and the reason `declared` and
    `inferred` are separate lists.

    That ROA says "This ROA contains further advice" — it names its situation.
    It ALSO says "My advice is to make no changes to your XYZ Superannuation
    Fund", while increasing the client's insurance cover. Both sentences are
    the document's own, so weighing them equally makes the most canonical
    further-advice example in the public sample set read as ambiguous.

    No change to one holding, inside advice that changes another, is not a
    s946B(7) no-action ROA — that basis needs the advice overall to be to take
    no action. The document's own statement of its basis is the better
    evidence, so it wins.
    """
    flag = _roa_flag(
        "Record of Advice. This ROA contains further advice to the advice you "
        "received in your Statement of Advice. My advice is to make no changes "
        "to your XYZ Superannuation Fund, and to increase your life cover."
    )

    assert flag["determination"] == "proposed"
    assert flag["proposed_basis"] == "further_advice"


def test_an_inferred_basis_still_decides_when_nothing_is_declared():
    """The split must not mute the inferred signals — most hold/no-action ROAs
    never cite s946B(7) by name, so inference is all there is for them.
    """
    flag = _roa_flag(
        "Record of Advice. Client: A Patel. Having reviewed your portfolio we "
        "recommend you take no action at this time."
    )

    assert flag["determination"] == "proposed"
    assert flag["proposed_basis"] == "hold_no_action"


def test_consequences_of_advice_are_not_hold_signals():
    """Regression from INFO 266 attachment 1: "you will retain your existing
    policy features and benefits" describes what follows from the advice, not
    a recommendation to hold. Retain/continue-to-hold phrasing is compatible
    with further advice that changes something else, so it is not a signal for
    any basis.
    """
    flag = _roa_flag(
        "Record of Advice. The premium remains competitive and you will retain "
        "your existing policy features and benefits."
    )

    assert flag["determination"] == "absent"


def test_it_fires_on_every_roa_including_an_unambiguous_one():
    """The one rule in the set that fires on a property of the type rather
    than on an anomaly. An ROA's basis is not recorded by classifying it as an
    ROA, and the basis decides the content the record must carry — so there is
    no ROA for which the question doesn't arise.
    advice_classification_reference.md §6 puts exactly this against the ROA
    row: "Medium: confirm which of 4 bases".
    """
    for _basis, text in BASES:
        assert _roa_flag(text)["determination"] == "proposed"


@pytest.mark.parametrize("doc_type", ["soa", "fsg", "pds", "authority_to_proceed", None])
def test_it_fires_on_nothing_but_an_roa(doc_type):
    """Including an SOA that cites an ROA. The rule keys on the classified
    type, not on the words in the document.
    """
    text = (
        "Statement of Advice prepared for J Client. Future adjustments may be "
        "confirmed by Record of Advice where there is no material change."
    )
    assert evaluate_flags(doc_type, text) == []


def test_severity_and_wording_come_from_the_knowledge_base():
    """Ground rule #1. The flag's severity and its explanation are data; this
    fails if either is ever copied into Python.
    """
    rule = _RULES["roa_basis_unconfirmed"]
    flag = _roa_flag(BASES[0][1])

    assert flag["severity"] == rule["severity"] == "medium"
    assert flag["why"] == rule["why"]
    assert flag["asks"] == rule["asks"]


def test_a_new_basis_signal_needs_no_code_change(tmp_path, monkeypatch):
    """Ground rule #1 again, as a property rather than a promise: a phrase
    added to a basis's `basis_signals` in the knowledge base changes the answer with
    no Python touched. This is how a signal that misfires on real firm files
    gets corrected — and how a fifth basis would be added if the law grew one.

    The knowledge base is loaded at import from the working directory, so the
    test runs the real module against an edited copy of the real file.
    """
    import importlib

    text = "Record of Advice. Client: R Hale. Advice given on a nil-transaction basis."
    assert _roa_flag(text)["determination"] == "absent"

    kb = json.loads(json.dumps(_KB))
    roa = next(d for d in kb["documents"] if d["id"] == "roa")
    kind = next(k for k in roa["legislation"]["four_kinds"] if k["id"] == "no_buy_sell")
    kind["basis_signals"]["declared"].append("nil-transaction basis")
    (tmp_path / "knowledge_base.json").write_text(json.dumps(kb))

    monkeypatch.chdir(tmp_path)
    import flags as flags_module

    try:
        edited = importlib.reload(flags_module)
        flag = edited.evaluate_flags("roa", text)[0]
        assert flag["determination"] == "proposed"
        assert flag["proposed_basis"] == "no_buy_sell"
        assert flag["matched_signals"] == ["nil-transaction basis"]
    finally:
        monkeypatch.undo()
        importlib.reload(flags_module)  # restore the real KB for other tests


def test_the_engine_never_evaluates_a_rule_it_lacks_evidence_for():
    """Every registered evaluator must belong to a rule the knowledge base
    declares stateless. A stateful rule needs other documents for the same
    client, which nothing persists yet (#8) — so registering one would report
    a check that never happened.
    """
    for rule_id in EVALUATORS:
        assert _RULES[rule_id]["evaluation"] == "stateless", rule_id


def test_every_rule_declares_how_it_can_be_evaluated():
    """So coverage stays legible: what the engine could run today, and what is
    waiting on persistence.
    """
    allowed = set(_KB["edge_case_flags"]["evaluation_values"])
    for rule in _KB["edge_case_flags"]["rules"]:
        assert rule.get("evaluation") in allowed, rule["id"]


def test_every_basis_says_whether_a_real_example_exists():
    """Three of the four bases have no real document to test against, and a
    signal list looks equally authoritative whether or not anything checked
    it. `example_status` makes the difference visible instead of leaving it to
    be inferred from silence. See issue #33.
    """
    roa = next(d for d in _KB["documents"] if d["id"] == "roa")
    kinds = roa["legislation"]["four_kinds"]

    for kind in kinds:
        assert kind["example_status"].strip(), kind["id"]

    untested = [k["id"] for k in kinds if k["example_status"].startswith("NO REAL EXAMPLE")]
    assert set(untested) == {"hold_no_action", "small_investment", "no_buy_sell"}
