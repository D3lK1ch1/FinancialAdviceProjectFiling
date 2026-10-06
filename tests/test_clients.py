from pathlib import Path

import pytest

from clients import find_client_candidates
from parser import parse_pdf

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_finds_labelled_client_name_with_page_and_context():
    """'Client name: <name>' yields the name, the label that found it, its page and context."""
    candidates = find_client_candidates(["Record of Advice", "Client name: George Baker Date of advice: 1 May 2021"])

    assert len(candidates) == 1
    assert candidates[0]["raw"] == "George Baker"
    assert candidates[0]["label"] == "client name"
    assert candidates[0]["page"] == 2
    assert "Client name: George Baker" in candidates[0]["context"]


def test_name_stops_at_an_all_capitals_word_from_a_neighbouring_column():
    """Layout extraction interleaves side columns: 'Nick Rossi AFS licensees' is the name 'Nick Rossi'."""
    candidates = find_client_candidates(["TIP: Authorised Client name: Nick Rossi AFS licensees and"])

    assert [c["raw"] for c in candidates] == ["Nick Rossi"]


def test_name_stops_where_the_next_field_begins():
    """'Account name: Wendy Zhang Account number: 12345' is the name 'Wendy Zhang', not 'Wendy Zhang Account'."""
    candidates = find_client_candidates(["Account name: Wendy Zhang Account number: 12345"])

    assert [c["raw"] for c in candidates] == ["Wendy Zhang"]
    assert candidates[0]["label"] == "account name"


def test_joint_names_are_kept_whole_not_split_or_chosen_between():
    """'Joe and Sue Black' stays one candidate: deciding what a joint client means is not this step's job."""
    candidates = find_client_candidates(["Client name: Joe and Sue Black"])

    assert [c["raw"] for c in candidates] == ["Joe and Sue Black"]


def test_label_with_no_name_after_it_is_not_a_candidate():
    """'client name' in running text ('the client name must appear') is a mention, not a name."""
    assert find_client_candidates(["The client name must appear on every page."]) == []


def test_label_match_ignores_capitals():
    """'CLIENT NAME:' and 'client name:' are the same label."""
    candidates = find_client_candidates(["CLIENT NAME: John Patel"])

    assert [c["raw"] for c in candidates] == ["John Patel"]


def test_no_labels_means_no_candidates():
    """An FSG names no client: nothing is found, rather than something guessed."""
    assert find_client_candidates(["Financial Services Guide", "About our fees"]) == []


@pytest.mark.samples
@pytest.mark.parametrize(
    "file, expected",
    [
        ("ROA_INFO266_att1_retain_modify.pdf", ["Nick Rossi"]),
        ("ROA_INFO266_att2_nochange.pdf", ["George Baker"]),
        ("ROA_INFO266_att3_stockbroker.pdf", ["Wendy Zhang"]),
        ("SOA_INFO267_limited_advice.pdf", ["John Patel"]),
        ("SOA_RG90_scaled_advice.pdf", ["Brad and Zara Black"]),
        ("FSG_AustralianSuper.pdf", []),
        ("FSG_PeninsulaWealth.pdf", []),
        ("FSG_UniSuper.pdf", []),
        ("PDS_AustralianEthicalSuper.pdf", []),
        ("PDS_AustralianSuper.pdf", []),
    ],
)
def test_real_samples(file, expected):
    """Every name each real sample labels as its client, and none from documents that name no client.

    The equality is the negative check too: the advisers (Sarah Johnson, Tom Baker, Sally
    Chong) and the INFO 267 client's wife (Jane) are named in these files and must not appear.
    """
    parsed = parse_pdf(str(SAMPLES / file), file)

    assert sorted({c["raw"] for c in find_client_candidates(parsed["pages"])}) == expected
