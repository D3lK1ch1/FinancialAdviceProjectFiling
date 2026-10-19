import re
from datetime import date

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))

_NUMERIC_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
_MONTH_NAME_DATE = re.compile(
    rf"\b\d{{1,2}}\s+(?:{_MONTH_PATTERN})\.?\s+\d{{4}}\b", re.IGNORECASE
)

_CONTEXT_CHARS = 40


def find_date_candidates(pages: list[str]) -> list[dict]:
    candidates = []
    for page_number, page_text in enumerate(pages, start=1):
        normalized = re.sub(r"\s+", " ", page_text).strip()
        matches = sorted(
            list(_NUMERIC_DATE.finditer(normalized))
            + list(_MONTH_NAME_DATE.finditer(normalized)),
            key=lambda m: m.start(),
        )
        for match in matches:
            start = max(0, match.start() - _CONTEXT_CHARS)
            end = min(len(normalized), match.end() + _CONTEXT_CHARS)
            candidates.append({
                "raw": match.group(),
                "page": page_number,
                "context": normalized[start:end],
            })
    return candidates


_NUMERIC_DATE_STRICT = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
_MONTH_NAME_DATE_STRICT = re.compile(
    rf"(\d{{1,2}})\s+({_MONTH_PATTERN})\.?\s+(\d{{4}})", re.IGNORECASE
)


def parse_day_first(raw: str) -> date | None:
    normalized = re.sub(r"\s+", " ", raw).strip()

    numeric_match = _NUMERIC_DATE_STRICT.fullmatch(normalized)
    if numeric_match:
        day, month, year = (int(g) for g in numeric_match.groups())
        return _safe_date(year, month, day)

    month_match = _MONTH_NAME_DATE_STRICT.fullmatch(normalized)
    if month_match:
        day = int(month_match.group(1))
        month = MONTHS[month_match.group(2).lower()]
        year = int(month_match.group(3))
        return _safe_date(year, month, day)

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def select_date(candidates: list[dict]) -> dict:
    parseable = [c for c in candidates if c.get("date") is not None]

    declared = [c for c in parseable if "date of advice" in c["context"].lower()]
    if declared:
        return {
            "candidates": candidates,
            "chosen": declared[0],
            "determination": "declared",
            "reason": "explicitly labelled 'date of advice'",
        }

    if not parseable:
        return {
            "candidates": candidates,
            "chosen": None,
            "determination": "absent",
            "reason": "no parseable date found in document",
        }

    boilerplate = _boilerplate_keys(parseable)
    non_boilerplate = [
        c for c in parseable if (c["raw"], c["context"]) not in boilerplate
    ]

    if not non_boilerplate:
        return {
            "candidates": candidates,
            "chosen": None,
            "determination": "ambiguous",
            "reason": "all candidate dates recur as repeated boilerplate; none clearly the advice date",
        }

    distinct_dates = {c["date"] for c in non_boilerplate}
    if len(distinct_dates) == 1:
        reason = (
            "only non-boilerplate date found"
            if len(non_boilerplate) == 1
            else "same date confirmed by multiple mentions"
        )
        return {
            "candidates": candidates,
            "chosen": non_boilerplate[0],
            "determination": "inferred",
            "reason": reason,
        }

    return {
        "candidates": candidates,
        "chosen": None,
        "determination": "ambiguous",
        "reason": "multiple candidate dates, none clearly the advice date",
    }


def _boilerplate_keys(candidates: list[dict]) -> set:
    pages_by_key: dict[tuple[str, str], set] = {}
    for c in candidates:
        key = (c["raw"], c["context"])
        pages_by_key.setdefault(key, set()).add(c["page"])
    return {key for key, pages in pages_by_key.items() if len(pages) >= 2}


def extract_dates(parsed: dict) -> dict:
    candidates = find_date_candidates(parsed["pages"])
    enriched = [dict(c, date=parse_day_first(c["raw"])) for c in candidates]
    return select_date(enriched)
