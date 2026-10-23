from pathlib import Path

import pytest

from clients import choose_client, client_folder_name, find_client_candidates, party_type
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


# --- client_folder_name (#6) ---------------------------------------------------
# The rules are Bella's: client_model.name_format (14 Oct) and joint_client (9 Oct).


@pytest.mark.parametrize("raw, folder", [
    ("George Baker", "Baker, George"),
    ("JOHN SMITH", "Smith, John"),                       # normal capitals, whatever the document uses
    ("Dr John Smith", "Smith, Dr John"),                 # titles kept, after the comma
    ("Mr John Smith", "Smith, Mr John"),
    ("Dr. John Smith", "Smith, Dr John"),
    ("Anna van der Berg", "van der Berg, Anna"),         # the particles belong to the surname
    ("ANNA VAN DER BERG", "van der Berg, Anna"),
    ("Mary-Jane O'BRIEN", "O'Brien, Mary-Jane"),
    ("Brad and Zara Black", "Black, Brad & Zara"),       # joint: one folder, names kept together
    ("Brad & Zara Black", "Black, Brad & Zara"),
    ("Brad Black and Zara Black", "Black, Brad & Zara"),
])
def test_a_found_name_becomes_its_folder_name(raw, folder):
    result = client_folder_name(raw)

    assert result["folder"] == folder
    assert result["reason"] is None


@pytest.mark.parametrize("raw, why", [
    ("Smith", "no first name"),
    ("Mr and Mrs Smith", "no first name"),
    ("Brad Black and Zara Smith", "two different surnames"),
    ("Ann and Bob and Cy Lee", "one or two people"),
    ("and", "one or two people"),
])
def test_a_name_that_cannot_be_read_safely_gets_no_folder_and_a_reason(raw, why):
    result = client_folder_name(raw)

    assert result["folder"] is None
    assert why in result["reason"]


def test_mixed_case_is_left_as_the_document_wrote_it():
    """'McDonald' is right as written. Recapitalising it would give 'Mcdonald'."""
    assert client_folder_name("Ian McDonald")["folder"] == "McDonald, Ian"


def test_titles_and_particles_come_from_the_knowledge_base():
    from kb import KB

    name_format = KB["client_model"]["name_format"]
    assert "Dr" in name_format["titles"]
    assert "van" in name_format["surname_particles"]


# --- Finding names the 14 Oct review said were missed (#6) -----------------------


@pytest.mark.parametrize("text, found", [
    ("Client name: JOHN SMITH Date of advice: 1 May 2024", "JOHN SMITH"),
    ("Client name: Anna van der Berg Adviser: Sam Lee", "Anna van der Berg"),
    ("Client name: ABC Pty Ltd", "ABC Pty Ltd"),
    ("Client name: SMITH FAMILY SMSF", "SMITH FAMILY SMSF"),
    ("Client name: John Smith ATF Smith Family Trust", "John Smith ATF Smith Family Trust"),
    ("Client name: John Smith as trustee for Smith Family Trust", "John Smith ATF Smith Family Trust"),
    ("Client name: Dr John Smith", "Dr John Smith"),
])
def test_names_the_review_found_missing_are_now_found(text, found):
    assert [c["raw"] for c in find_client_candidates([text])] == [found]


def test_a_name_in_capitals_does_not_swallow_a_capitalised_column_after_a_mixed_case_name():
    """The reason all-capitals words were refused at all: 'Nick Rossi AFS licensees'."""
    assert [c["raw"] for c in find_client_candidates(["Client name: Nick Rossi AFS licensees"])] == ["Nick Rossi"]


def test_a_trailing_particle_is_not_kept():
    assert [c["raw"] for c in find_client_candidates(["Client name: Ann de"])] == ["Ann"]


# --- Party type and entity folders (#6) ---------------------------------------------


@pytest.mark.parametrize("raw, kind", [
    ("George Baker", "individual"),
    ("Brad and Zara Black", "joint"),
    ("ABC Pty Ltd", "entity"),
    ("Smith Family Trust", "entity"),
    ("SMITH FAMILY SMSF", "entity"),
    ("John Smith ATF Smith Family Trust", "entity"),
])
def test_party_type(raw, kind):
    assert party_type(raw) == kind


@pytest.mark.parametrize("raw, folder", [
    ("ABC Pty Ltd", "ABC Pty Ltd"),                            # the entity's own name, not reordered
    ("ABC PTY LTD", "ABC Pty Ltd"),
    ("SMITH FAMILY TRUST", "Smith Family Trust"),
    ("John Smith ATF Smith Family Trust", "Smith Family Trust"),  # trustee named: file under the trust
])
def test_an_entity_is_filed_under_its_own_name(raw, folder):
    result = client_folder_name(raw)

    assert result == {"folder": folder, "party_type": "entity", "reason": None}


def test_a_trustee_with_no_trust_named_gets_no_folder():
    result = client_folder_name("John Smith ATF")

    assert result["folder"] is None
    assert "no trust or company" in result["reason"]


# --- choose_client (#6) ----------------------------------------------------------


def _found(*raws):
    return [{"raw": raw} for raw in raws]


def test_one_client_named_everywhere_is_proposed():
    client = choose_client(_found("George Baker", "GEORGE BAKER"))

    assert client["folder"] == "Baker, George"
    assert client["party_type"] == "individual"
    assert client["ambiguous"] is False
    assert client["reason"] is None


def test_no_client_named_is_not_ambiguous_but_has_a_reason():
    client = choose_client([])

    assert client["folder"] is None
    assert client["ambiguous"] is False
    assert "labels no client" in client["reason"]


@pytest.mark.parametrize("raws", [
    ("John Smith", "Jane Jones"),
    ("Brad and Zara Black", "Brad Black"),   # joint vs individual is not guessed
    ("John Smith", "Jones"),                 # an unreadable name that isn't part of the chosen one
])
def test_two_different_clients_are_never_chosen_between(raws):
    client = choose_client(_found(*raws))

    assert client["folder"] is None
    assert client["ambiguous"] is True
    assert "adviser chooses" in client["reason"]


def test_a_shorter_mention_of_the_same_client_is_not_a_second_client():
    assert choose_client(_found("John Smith", "Smith"))["folder"] == "Smith, John"


@pytest.mark.samples
@pytest.mark.parametrize(
    "file, folder",
    [
        ("ROA_INFO266_att1_retain_modify.pdf", "Rossi, Nick"),
        ("ROA_INFO266_att2_nochange.pdf", "Baker, George"),
        ("ROA_INFO266_att3_stockbroker.pdf", "Zhang, Wendy"),
        ("SOA_INFO267_limited_advice.pdf", "Patel, John"),
        ("SOA_RG90_scaled_advice.pdf", "Black, Brad & Zara"),
        ("FSG_PeninsulaWealth.pdf", None),
        ("PDS_AustralianSuper.pdf", None),
    ],
)
def test_real_samples_propose_their_client_folder(file, folder):
    parsed = parse_pdf(str(SAMPLES / file), file)

    client = choose_client(find_client_candidates(parsed["pages"]))

    assert client["folder"] == folder
    assert client["ambiguous"] is False


def test_prepared_for_labels_the_client():
    """The cover table of an SOA often reads 'Prepared for <names>' (Bella, 23 Oct 2026)."""
    page = "Statement of Advice\n Prepared for                    Brad Black and Zara Black\n Prepared by    Daniel Archer"
    candidates = find_client_candidates([page])

    assert [c["label"] for c in candidates] == ["prepared for"]
    assert choose_client(candidates)["folder"] == "Black, Brad & Zara"
