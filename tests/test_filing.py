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


# --- Advice event folder (#10, subject decided 1 Oct) ------------------------

from filing import advice_subject, proposed_event_folder  # noqa: E402

# A client's circumstances, as every SOA must set them out. These name areas
# the advice is not about — the reason the subject is read from scope only.
_CIRCUMSTANCES = (
    "Brad has $100,000 in a superannuation fund. They have a $440,000 mortgage. "
    "Payment from Centrelink (Family Tax Benefit) $1,896. "
)
_EXCLUSIONS = "My advice does not cover the suitability of your existing superannuation. "


def test_subject_comes_from_the_scope_statement_not_the_circumstances():
    text = _CIRCUMSTANCES + "This advice is about your personal insurance needs. " + _EXCLUSIONS

    result = advice_subject(text)

    assert result["subject"] == "Insurance"
    assert "Superannuation" in result["also_mentioned"]
    assert "Centrelink" in result["also_mentioned"]


def test_several_areas_join_in_kb_order():
    text = (
        "Joe and Sue, you have asked for my advice about how to invest the $155,000 "
        "and how you can protect your family in case either of you should die or become sick."
    )

    assert advice_subject(text)["subject"] == "Insurance & Investment"


@pytest.mark.parametrize(
    "scope",
    [
        "My advice is to apply to increase your IP policy.",
        "This advice is about your risk insurance.",
        "You wanted advice about personal risk cover for the family.",
        "This advice is about how to protect your income if you are unable to work.",
    ],
)
def test_insurance_is_recognised_in_adviser_wording(scope):
    assert advice_subject(scope)["areas"] == ["Insurance"]


@pytest.mark.parametrize(
    "scope",
    [
        "This advice is about your investment risk profile.",
        "My advice is to keep the cover sheet with your records.",
        "This advice is about what you will need to invest.",
    ],
)
def test_bare_risk_cover_and_will_do_not_count(scope):
    areas = advice_subject(scope)["areas"]

    assert "Insurance" not in areas
    assert "Estate planning" not in areas


def test_no_scope_statement_means_no_subject_and_the_reviewer_supplies_it():
    result = advice_subject(_CIRCUMSTANCES)

    assert result["subject"] is None
    assert result["reason"] == "no scope statement found"
    assert result["also_mentioned"]  # still offered to the reviewer


def test_soa_event_folder():
    text = "This advice is about your personal insurance needs."

    result = proposed_event_folder("soa", text, _dated(date(2024, 3, 14)))

    assert result["folder"] == "2024-03 — Insurance"


def test_event_folder_is_not_named_after_its_record():
    """The folder holds the whole event, so neither the record type nor the
    ROA situation is in its name — they are in the record's filename."""
    text = "My advice is to make no changes to your XYZ Superannuation Fund. My advice is to apply to increase your IP policy."

    result = proposed_event_folder("roa", text, _dated(date(2025, 6, 2)))

    assert result["folder"] == "2025-06 — Superannuation & Insurance"
    assert "ROA" not in result["folder"]


def test_only_an_advice_record_names_an_event():
    result = proposed_event_folder("fact_find", "This advice is about insurance.", _dated(date(2024, 3, 1)))

    assert result["folder"] is None
    assert "#8" in result["reason"]


def test_no_folder_without_a_usable_date():
    result = proposed_event_folder(
        "soa", "This advice is about your insurance.",
        {"chosen": None, "determination": "ambiguous", "reason": "x"},
    )

    assert result["folder"] is None
    assert result["subject"]["subject"] == "Insurance", "the subject is still offered"


def test_no_folder_without_a_subject():
    result = proposed_event_folder("soa", _CIRCUMSTANCES, _dated(date(2024, 3, 14)))

    assert result["folder"] is None
    assert "reviewer" in result["reason"]


def test_every_area_in_the_kb_has_signals():
    for area in _KB["filing_model"]["advice_event"]["subject"]["areas"]:
        assert area["signals"], area["name"]


# --- Advice stage, shown per document (decided 9 Oct) --------------------------

from filing import advice_stages, proposed_filing  # noqa: E402


def test_a_type_in_two_stages_lists_both_in_order():
    assert advice_stages("soa") == ["3 Advice construction", "4 Advice delivery"]


def test_a_type_at_every_stage_says_so_instead_of_listing_them():
    assert advice_stages("file_note") == [_KB["filing_model"]["stage_label"]["every_stage_label"]]


def test_no_type_means_no_stage():
    assert advice_stages(None) == []


@pytest.mark.parametrize("doc", _KB["documents"], ids=lambda d: d["id"])
def test_every_type_has_a_stage_in_the_kb(doc):
    assert advice_stages(doc["id"]), doc["id"]


# --- The whole proposal ----------------------------------------------------------

_SOA_PAGES = ["Date of advice: 14 March 2024", "This advice is about your personal insurance."]


def test_proposed_filing_gives_each_part():
    result = proposed_filing("soa", " ".join(_SOA_PAGES), _SOA_PAGES, [], "Nguyen SOA.pdf")

    assert result["event_folder"] == "2024-03 — Insurance"
    assert result["filename"] == "2024-03-14 SOA.pdf"
    assert result["stages"] == ["3 Advice construction", "4 Advice delivery"]
    assert result["date"] == "2024-03-14"


def test_proposed_filing_never_names_a_client_folder_yet():
    result = proposed_filing("soa", " ".join(_SOA_PAGES), _SOA_PAGES, [], "a.pdf")

    assert result["client_folder"] is None
    assert "GH#6" in result["client_reason"]


def test_proposed_filing_without_a_date_says_why_for_each_part():
    pages = ["This advice is about your personal insurance."]

    result = proposed_filing("soa", pages[0], pages, [], "a.pdf")

    assert result["event_folder"] is None and result["event_reason"]
    assert result["filename"] is None and result["filename_reason"]
