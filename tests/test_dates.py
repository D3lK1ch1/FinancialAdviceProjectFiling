from datetime import date
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from dates import extract_dates, find_date_candidates, parse_day_first, select_date
from parser import parse_pdf


def _pdf_with_pages(*page_texts: str) -> BytesIO:
    """Duplicated from tests/test_parser.py rather than imported, matching the
    project's one-file-one-concern test style — builds a real multi-page PDF
    pypdf can extract text from, using only project dependencies.
    """
    writer = PdfWriter()
    for text in page_texts:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 14 Tf 20 250 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)

    buf = BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf


def test_finds_numeric_dmy_candidate_with_context():
    """A slash-separated numeric date is recognised with its surrounding text as context."""
    candidates = find_date_candidates(["Dated 03/04/2025 at Sydney"])
    assert len(candidates) == 1
    assert candidates[0]["raw"] == "03/04/2025"
    assert candidates[0]["page"] == 1
    assert "Dated" in candidates[0]["context"]
    assert "Sydney" in candidates[0]["context"]


def test_finds_month_name_candidate():
    """A day + full month name + year date is recognised as a candidate."""
    candidates = find_date_candidates(["Signed this 3 April 2025 by the adviser"])
    assert len(candidates) == 1
    assert candidates[0]["raw"] == "3 April 2025"


def test_finds_candidates_across_pages_with_correct_page_numbers():
    """Each candidate records the 1-indexed page it was found on, not just its position in the joined text."""
    candidates = find_date_candidates([
        "First page, dated 01/02/2024",
        "Second page, dated 03/04/2025",
    ])
    pages_found = {c["page"] for c in candidates}
    assert pages_found == {1, 2}
    by_page = {c["page"]: c["raw"] for c in candidates}
    assert by_page[1] == "01/02/2024"
    assert by_page[2] == "03/04/2025"


def test_ignores_numbers_that_are_not_date_shaped():
    """Bare numbers without date separators must not be treated as date candidates."""
    candidates = find_date_candidates(["Account balance 840000 reference 123456"])
    assert candidates == []


def test_no_candidates_on_text_with_no_dates():
    """Plain text with no dates at all returns an empty candidate list."""
    candidates = find_date_candidates(["This document contains no dates whatsoever."])
    assert candidates == []


def test_parses_ambiguous_numeric_day_first():
    """03/04/2025 is 3 April in an AU document, never 4 March — the exact case named in GH#8."""
    assert parse_day_first("03/04/2025") == date(2025, 4, 3)


def test_parses_unambiguous_numeric_still_reads_day_first():
    """15/04/2025 has only one valid reading, but the day-first rule must apply consistently, not just when convenient."""
    assert parse_day_first("15/04/2025") == date(2025, 4, 15)


def test_rejects_invalid_numeric_date_rather_than_reordering():
    """31/04/2025 is invalid (April has 30 days) — must be rejected, not reinterpreted as month-first."""
    assert parse_day_first("31/04/2025") is None


def test_parses_month_name_date():
    """A day + full month name + year date parses to the same date, day-first by construction."""
    assert parse_day_first("3 April 2025") == date(2025, 4, 3)


def test_parses_abbreviated_month_name():
    """Abbreviated month names (Apr) parse the same as the full name."""
    assert parse_day_first("3 Apr 2025") == date(2025, 4, 3)


def test_rejects_two_digit_year():
    """A 2-digit year is a genuine century ambiguity with no textual evidence to resolve it — reject, never assume 20xx."""
    assert parse_day_first("03/04/25") is None


def test_rejects_unparseable_text():
    """Text that isn't date-shaped at all returns None rather than raising."""
    assert parse_day_first("not a date") is None


def test_selects_sole_candidate():
    """A single parseable candidate is chosen with no competition to resolve."""
    candidates = [
        {"raw": "03/04/2025", "page": 1, "context": "Signed 03/04/2025 by adviser", "date": date(2025, 4, 3)},
    ]
    result = select_date(candidates)
    assert result["determination"] == "inferred"
    assert result["chosen"]["raw"] == "03/04/2025"


def test_declared_beats_repeated_candidate():
    """An explicit 'date of advice' label wins even over a date that recurs across pages."""
    boilerplate_context = "Australian Securities and Investments Commission 1 December 2024 Page"
    candidates = [
        {"raw": "1 December 2024", "page": 1, "context": boilerplate_context, "date": date(2024, 12, 1)},
        {"raw": "1 December 2024", "page": 2, "context": boilerplate_context, "date": date(2024, 12, 1)},
        {"raw": "3 April 2025", "page": 1, "context": "Date of advice: 3 April 2025 given today", "date": date(2025, 4, 3)},
    ]
    result = select_date(candidates)
    assert result["determination"] == "declared"
    assert result["chosen"]["raw"] == "3 April 2025"


def test_excludes_boilerplate_repeated_across_pages():
    """A date whose (raw, context) recurs near-identically on multiple pages is treated as a running header/footer, not content."""
    boilerplate_context = "Australian Securities and Investments Commission 1 December 2024 Page"
    candidates = [
        {"raw": "1 December 2024", "page": 1, "context": boilerplate_context, "date": date(2024, 12, 1)},
        {"raw": "1 December 2024", "page": 2, "context": boilerplate_context, "date": date(2024, 12, 1)},
        {"raw": "12 October 2021", "page": 1, "context": "The advice was given on 12 October 2021 after discussion", "date": date(2021, 10, 12)},
    ]
    result = select_date(candidates)
    assert result["determination"] == "inferred"
    assert result["chosen"]["raw"] == "12 October 2021"
    assert result["reason"] == "only non-boilerplate date found"


def test_same_date_confirmed_by_multiple_mentions_is_not_ambiguous():
    """Two mentions of the identical date in different sentences corroborate each other rather than compete — found via the real-sample spot-check on FSG_AustralianSuper.pdf, where '14 April 2025' appears once on the title page and once in an 'issued on' sentence on another page."""
    candidates = [
        {"raw": "14 April 2025", "page": 1, "context": "Financial Services Guide 14 April 2025 This Financial Services Guide", "date": date(2025, 4, 14)},
        {"raw": "14 April 2025", "page": 2, "context": "This FSG was issued on 14 April 2025. This may include", "date": date(2025, 4, 14)},
    ]
    result = select_date(candidates)
    assert result["determination"] == "inferred"
    assert result["chosen"]["date"] == date(2025, 4, 14)
    assert result["reason"] == "same date confirmed by multiple mentions"


def test_ambiguous_when_multiple_non_boilerplate_candidates_and_no_declared_label():
    """Two distinct, each-appearing-once dates with no declared label must not be guessed between — return ambiguous with the full candidate set."""
    candidates = [
        {"raw": "17 October 2019", "page": 1, "context": "SOA dated 17 October 2019 was provided", "date": date(2019, 10, 17)},
        {"raw": "30 June 2022", "page": 2, "context": "tax return due 30 June 2022 noted here", "date": date(2022, 6, 30)},
    ]
    result = select_date(candidates)
    assert result["determination"] == "ambiguous"
    assert result["chosen"] is None
    assert result["candidates"] == candidates


def test_absent_on_empty_candidate_list():
    """No candidates at all means no_date, not a guess from file metadata."""
    result = select_date([])
    assert result["determination"] == "absent"
    assert result["chosen"] is None


def test_absent_but_returns_original_candidates_when_all_unparseable():
    """Even when nothing parses, the raw candidate set is still returned — the literal 'candidate set plus why' requirement from GH#8."""
    candidates = [
        {"raw": "03/04/25", "page": 1, "context": "Dated 03/04/25 only", "date": None},
    ]
    result = select_date(candidates)
    assert result["determination"] == "absent"
    assert result["chosen"] is None
    assert result["candidates"] == candidates


def test_extract_dates_returns_expected_shape():
    """The public entry point's output key set doesn't depend on document content."""
    result = extract_dates({"pages": ["nothing dated here"]})
    assert set(result.keys()) == {"candidates", "chosen", "determination", "reason"}


def test_extract_dates_end_to_end_on_synthetic_multi_page_document():
    """Candidate-finding, day-first parsing and declared-label selection thread through correctly end to end."""
    pages = [
        "Statement of Advice",
        "Date of advice: 03/04/2025",
        "Prepared for Jane Citizen",
    ]
    result = extract_dates({"pages": pages})
    assert result["determination"] == "declared"
    assert result["chosen"]["date"] == date(2025, 4, 3)


def test_extract_dates_fires_absent_on_dateless_document():
    """A document with no date-shaped text at all returns absent, never a guess from file metadata."""
    pages = ["This document contains no dates whatsoever."]
    result = extract_dates({"pages": pages})
    assert result["determination"] == "absent"
    assert result["chosen"] is None


def test_extract_dates_on_real_parse_pdf_output():
    """Proves extract_dates works against parse_pdf()'s actual return dict, not just a hand-built stand-in."""
    buf = _pdf_with_pages("Statement of Advice", "Date of advice: 03/04/2025")
    parsed = parse_pdf(buf, "generated.pdf")

    result = extract_dates(parsed)

    assert result["determination"] == "declared"
    assert result["chosen"]["date"] == date(2025, 4, 3)
