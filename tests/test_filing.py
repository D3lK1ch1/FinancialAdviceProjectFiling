"""Tests for filing.py's document filename (#10, pattern decided 1 Oct).

Plain data — date results and flags built inline — so they run on a bare clone.
"""

import json
from datetime import date

import pytest

from filing import proposed_filename

with open("knowledge_base.json") as f:
    _KB = json.load(f)


def _dated(d: date, determination: str = "declared") -> dict:
    return {"chosen": {"date": d}, "determination": determination, "reason": "test"}


def _roa_flag(situation: str | None) -> dict:
    return {"id": "roa_basis_unconfirmed", "proposed_basis": situation}


def test_soa_is_date_then_abbrev():
    result = proposed_filename("soa", _dated(date(2024, 3, 14)), [], "upload.pdf")

    assert result["filename"] == "2024-03-14 SOA.pdf"


def test_roa_carries_its_situation_when_one_was_proposed():
    result = proposed_filename(
        "roa", _dated(date(2025, 6, 2)), [_roa_flag("further_advice")], "x.pdf"
    )

    assert result["filename"] == "2025-06-02 ROA — further advice.pdf"


def test_roa_without_a_proposed_situation_asserts_none():
    """The flag left the situation open; the filename must not close it."""
    result = proposed_filename("roa", _dated(date(2025, 6, 2)), [_roa_flag(None)], "x.pdf")

    assert result["filename"] == "2025-06-02 ROA.pdf"


@pytest.mark.parametrize("doc", _KB["documents"], ids=lambda d: d["id"])
def test_every_type_is_named_from_its_kb_abbrev(doc):
    """No short name lives in Python — a new type is named as soon as the KB has it."""
    result = proposed_filename(doc["id"], _dated(date(2024, 1, 5)), [], "a.pdf")

    assert result["filename"] == f"2024-01-05 {doc['abbrev']}.pdf"


def test_an_inferred_date_is_usable():
    result = proposed_filename("fact_find", _dated(date(2024, 2, 20), "inferred"), [], "a.pdf")

    assert result["filename"] == "2024-02-20 Fact Find.pdf"
    assert result["reason"] == "inferred"


@pytest.mark.parametrize("determination", ["ambiguous", "absent"])
def test_no_usable_date_means_no_name_and_says_why(determination):
    """A guessed date reorders a client's advice history once sorted."""
    result = proposed_filename(
        "soa",
        {"chosen": None, "determination": determination, "reason": "nothing clear"},
        [],
        "a.pdf",
    )

    assert result["filename"] is None
    assert determination in result["reason"]


def test_no_type_means_no_name():
    result = proposed_filename(None, _dated(date(2024, 3, 14)), [], "a.pdf")

    assert result["filename"] is None


def test_nothing_from_the_uploaded_name_survives_but_its_extension():
    """The upload's name is routinely the client's name."""
    result = proposed_filename("soa", _dated(date(2024, 3, 14)), [], "Nguyen Family SOA FINAL v3.PDF")

    assert result["filename"] == "2024-03-14 SOA.pdf"
    assert "Nguyen" not in result["filename"]
