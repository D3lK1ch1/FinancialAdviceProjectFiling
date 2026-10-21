"""Filing proposals — what a document would be called and where it would go (#10).

A proposal only. Nothing here moves or writes a file: storage.py does that,
and only after a person approves (ground rule #2). Nothing here knows about
paths either — a name is a plain string, and the backend decides what it
means on its medium (ground rule #3).

Document filename, decided on #10 (1 Oct), with the client in front since
21 Oct (filing_model.file_name):

    <Surname>_<First name>_YYYY-MM-DD <abbrev>[ — <qualifier>].<ext>

    Nguyen_Lan_2024-03-14 SOA.pdf
    Black_Brad_Zara_2025-06-02 ROA — further advice.pdf

With no client chosen there is no client part: the client is never guessed.

Date first so files sort chronologically inside an event folder. The short
name is the document type's `abbrev` in knowledge_base.json, and the only
qualifier today is the ROA situation, when the flag could propose one. Every
word in the name comes from the knowledge base or the document's date — never
from the uploaded filename, which is routinely the client's name.

No usable date means no proposed name, with the reason. A filename built on a
guessed date reorders a client's advice history the moment it is sorted.
"""

import re
from pathlib import PurePath

from dates import extract_dates

from kb import KB as _KB

_ABBREV = {doc["id"]: doc["abbrev"] for doc in _KB["documents"]}
_FILE_NAME_SEPARATOR = _KB["filing_model"]["file_name"]["separator"]
_ROA_SITUATIONS = {
    s["id"]: s["kind"]
    for doc in _KB["documents"]
    if doc["id"] == "roa"
    for s in doc["legislation"]["situations"]
}

# Determinations from dates.select_date() that name one date to stand on.
_USABLE_DATE = {"declared", "inferred"}


def _qualifier(doc_type: str, flags: list[dict]) -> str | None:
    if doc_type != "roa":
        return None
    for flag in flags:
        situation = flag.get("proposed_basis")
        if situation in _ROA_SITUATIONS:
            return _ROA_SITUATIONS[situation].lower()
    # No situation proposed: the name says ROA and nothing more, rather than
    # asserting a situation the flag itself left open.
    return None


def client_prefix(client_folder: str | None) -> str | None:
    """The client part of a file name, from the client folder (filing_model.file_name).

    'Nguyen, Lan' -> 'Nguyen_Lan'; 'Black, Brad & Zara' -> 'Black_Brad_Zara'.
    A folder with no comma (a trust or company) is used whole.
    """
    if not client_folder:
        return None
    if ", " not in client_folder:
        return client_folder
    surname, first_names = client_folder.split(", ", 1)
    return _FILE_NAME_SEPARATOR.join([surname, *first_names.split(" & ")])


def proposed_filename(
    doc_type: str | None,
    date_result: dict,
    flags: list[dict] | None = None,
    original_filename: str = "",
    client_folder: str | None = None,
) -> dict:
    """The name a document would be filed under, or why there isn't one.

    `date_result` is dates.extract_dates()'s return; `flags` is
    flags.evaluate_flags()'s. Returns {"filename", "reason"} — filename is
    None whenever a part of it could not be stood behind.
    """
    if doc_type not in _ABBREV:
        return {"filename": None, "reason": "no document type to name it by"}

    chosen = date_result.get("chosen")
    if date_result.get("determination") not in _USABLE_DATE or not chosen:
        return {
            "filename": None,
            "reason": f"no usable date ({date_result.get('determination')}): "
            f"{date_result.get('reason')}",
        }

    name = f"{chosen['date'].isoformat()} {_ABBREV[doc_type]}"
    qualifier = _qualifier(doc_type, flags or [])
    if qualifier:
        name += f" — {qualifier}"

    # No client chosen, no client part: the reason is in client_reason.
    prefix = client_prefix(client_folder)
    if prefix:
        name = f"{prefix}{_FILE_NAME_SEPARATOR}{name}"

    # Only the extension is taken from the upload — never its stem.
    ext = PurePath(original_filename).suffix.lower() or ".pdf"
    return {"filename": name + ext, "reason": date_result["determination"]}


# --- Advice event folder -----------------------------------------------------
#
#     YYYY-MM — <subject>
#     2024-03 — Insurance
#     2025-06 — Superannuation & Insurance
#
# No record type in the name: the folder holds every document of the event,
# so it is not named after one of them (filing_model.advice_event.naming_note).
# The record type and ROA situation are in each document's filename instead.
#
# The subject is read from the advice record's own statement of scope, never
# from the whole document: an SOA must set out the client's circumstances, so
# the whole document reads the client's balance sheet, not the advice. The
# reasoning and the six-sample evidence are in filing_model.advice_event.subject.

_SUBJECT = _KB["filing_model"]["advice_event"]["subject"]
_SCOPE_PHRASES = [p.lower() for p in _SUBJECT["scope_phrases"]]
_AREAS = [
    (area["name"], [re.compile(r"\b" + re.escape(sig.lower())) for sig in area["signals"]])
    for area in _SUBJECT["areas"]
]
_ADVICE_RECORDS = {doc["id"] for doc in _KB["documents"] if doc.get("advice_record_role")}

# How far a scope statement may run when no full stop ends it — a heading or a
# table cell can swallow the punctuation in PDF extraction.
_SCOPE_MAX_CHARS = 300


def _areas_in(text: str) -> list[str]:
    return [name for name, signals in _AREAS if any(rx.search(text) for rx in signals)]


def scope_statements(text: str) -> list[str]:
    """The sentences where the document says what the advice is about."""
    flat = re.sub(r"\s+", " ", text).lower()
    statements = []
    for phrase in _SCOPE_PHRASES:
        for m in re.finditer(re.escape(phrase), flat):
            tail = flat[m.end(): m.end() + _SCOPE_MAX_CHARS]
            statements.append(phrase + tail.split(". ")[0])
    return statements


def advice_subject(text: str) -> dict:
    """{"subject", "areas", "also_mentioned", "reason"} for an advice record."""
    statements = scope_statements(text)
    areas = _areas_in(" ".join(statements))
    elsewhere = [a for a in _areas_in(re.sub(r"\s+", " ", text).lower()) if a not in areas]
    if not areas:
        return {
            "subject": None,
            "areas": [],
            "also_mentioned": elsewhere,
            "reason": "no scope statement found" if not statements
            else "scope statement names no known advice area",
        }
    return {
        "subject": _SUBJECT["join"].join(areas),
        "areas": areas,
        "also_mentioned": elsewhere,
        "reason": "from the document's scope statement",
    }


def proposed_event_folder(
    doc_type: str | None,
    text: str,
    date_result: dict,
) -> dict:
    """The advice event folder an advice record would open, or why there isn't one.

    Only an advice record names an event. Every other document belongs to the
    event of the record it links to, which needs other documents on hand —
    cross-document grouping, waiting on persistence in #8.
    """
    if doc_type not in _ADVICE_RECORDS:
        return {
            "folder": None,
            "subject": None,
            "reason": "only an advice record names an event; grouping this document needs other documents (#8)",
        }

    subject = advice_subject(text)
    chosen = date_result.get("chosen")
    if date_result.get("determination") not in _USABLE_DATE or not chosen:
        return {"folder": None, "subject": subject,
                "reason": f"no usable date ({date_result.get('determination')})"}
    if subject["subject"] is None:
        return {"folder": None, "subject": subject,
                "reason": f"{subject['reason']} — the reviewer supplies the subject"}

    folder = f"{chosen['date'].strftime('%Y-%m')} — {subject['subject']}"
    return {"folder": folder, "subject": subject, "reason": subject["reason"]}


# --- Advice process stage ------------------------------------------------------
#
# Shown on each document, not a folder layer (filing_model.stage_label). Read
# from advice_process_stages[].typical_docs, so a type can sit in more than
# one stage — an SOA is both constructed and delivered.

_STAGES = _KB["advice_process_stages"]
_EVERY_STAGE = _KB["filing_model"]["stage_label"]["every_stage_label"]


def advice_stages(doc_type: str | None) -> list[str]:
    """The stage names a document type belongs to, in process order."""
    found = [f"{s['stage']} {s['name']}" for s in _STAGES if doc_type in s["typical_docs"]]
    # A type that turns up at every stage (a file note) says nothing by listing them.
    return [_EVERY_STAGE] if found and len(found) == len(_STAGES) else found


# --- Planning step folder ------------------------------------------------------
#
# Inside an advice event, each document sits in a folder for its practical
# planning step (filing_model.stage_folders, decided 21 Oct). A type in no step
# folder files at the event level.

_STEP_FOLDERS = _KB["filing_model"]["stage_folders"]["folders"]


def step_folder(doc_type: str | None) -> dict:
    """{"folder", "reason"}: the step folder inside the event, or None and why."""
    for folder in _STEP_FOLDERS:
        if doc_type in folder["docs"]:
            steps = " and ".join(str(s) for s in folder["steps"])
            return {"folder": folder["name"], "reason": f"planning step {steps}"}
    return {"folder": None, "reason": "no step folder for this type: it files at the event level"}


# --- The whole proposal --------------------------------------------------------

def proposed_filing(
    doc_type: str | None,
    text: str,
    pages: list[str],
    flags: list[dict] | None = None,
    original_filename: str = "",
    client: dict | None = None,
) -> dict:
    """Where one document would be filed, part by part, as /ingest reports it.

    Each part is either a name or None with the reason it is missing. Still a
    proposal: nothing here writes, and the parts are not joined into a path,
    because a path with a hole in it reads as a real destination.

    The client folder is the one clients.choose_client() proposed, or None
    with its reason: no client named, a name that can't be read safely, or
    more than one client (GH#6). Still a proposal a person confirms.
    """
    date_result = extract_dates({"pages": pages})
    chosen = date_result.get("chosen")
    client_folder = client["folder"] if client else None
    name = proposed_filename(doc_type, date_result, flags, original_filename, client_folder)
    event = proposed_event_folder(doc_type, text, date_result)
    step = step_folder(doc_type)
    return {
        "client_folder": client_folder,
        "client_reason": client["reason"] if client else "no client was looked for",
        "event_folder": event["folder"],
        "event_reason": event["reason"],
        "step_folder": step["folder"],
        "step_reason": step["reason"],
        "stages": advice_stages(doc_type),
        "filename": name["filename"],
        "filename_reason": name["reason"],
        "date": chosen["date"].isoformat() if chosen and chosen.get("date") else None,
        "date_determination": date_result.get("determination"),
    }
