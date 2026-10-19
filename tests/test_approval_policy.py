"""knowledge_base.json's approval_policy stays consistent with the rest of the KB.

The policy is domain data the Approve/Edit/Reject screen will read (#4). These
tests keep it honest: every role, document type and flag it names exists, and
the decisions Bella made on 1 Oct 2026 are pinned rather than implied.
"""

import json

import pytest

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_POLICY = _KB["approval_policy"]
_DOC_IDS = {d["id"] for d in _KB["documents"]}
_RULE_IDS = {r["id"] for r in _KB["edge_case_flags"]["rules"]}


def test_only_an_adviser_or_compliance_approves():
    assert set(_POLICY["approvers"]) == {"adviser", "compliance"}
    for role, spec in _POLICY["roles"].items():
        assert spec["can_approve"] is (role in _POLICY["approvers"]), role


def test_only_compliance_clears_a_hard_stop():
    clearers = {r for r, spec in _POLICY["roles"].items() if spec["can_clear_hard_stop"]}
    assert clearers == {"compliance"}


def test_everyone_can_prepare_a_proposal():
    """Staff correct proposals; the decision stays with an approver."""
    for role, spec in _POLICY["roles"].items():
        assert spec["can_view"] and spec["can_edit"], role


def test_own_clients_only_names_real_types_and_covers_the_advice_records():
    own = set(_POLICY["own_clients_only"])
    assert own <= _DOC_IDS
    advice_records = {d["id"] for d in _KB["documents"] if d.get("advice_record_role")}
    assert advice_records <= own


def test_every_document_type_has_a_reviewer_check():
    assert set(_POLICY["checks_by_type"]) == _DOC_IDS
    assert all(text.strip() for text in _POLICY["checks_by_type"].values())


def test_flag_effects_name_real_rules_and_real_effects():
    effects = set(_POLICY["flag_effects"])
    for rule, effect in _POLICY["flag_effect_by_rule"].items():
        assert rule in _RULE_IDS, rule
        assert effect in effects, rule
        assert _POLICY["flag_effect_by_rule_why"][rule].strip(), rule


@pytest.mark.parametrize(
    "rule", ["atp_without_advice_record", "risk_mismatch", "fact_find_after_soa", "multi_doc_bundle"]
)
def test_the_compliance_red_flags_are_hard_stops(rule):
    assert _POLICY["flag_effect_by_rule"][rule] == "hard_stop"


def test_every_rule_is_either_decided_or_listed_as_undecided():
    """Nothing falls through silently: a new rule must be placed, or named as
    waiting for a decision."""
    decided = set(_POLICY["flag_effect_by_rule"])
    undecided = set(_POLICY["not_yet_decided"])
    assert not decided & undecided
    assert decided | undecided == _RULE_IDS


def test_every_document_type_sits_in_at_least_one_stage():
    """The guard that would have caught PDS missing from the stage map."""
    staged = {d for stage in _KB["advice_process_stages"] for d in stage["typical_docs"]}
    assert _DOC_IDS <= staged, _DOC_IDS - staged


def test_file_notes_sit_in_every_stage():
    for stage in _KB["advice_process_stages"]:
        assert "file_note" in stage["typical_docs"], stage["stage"]
