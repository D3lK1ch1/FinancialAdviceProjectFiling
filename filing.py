"""Filing proposals — what a document would be called and where it would go (#10).

A proposal only. Nothing here moves or writes a file: storage.py does that,
and only after a person approves (ground rule #2). Nothing here knows about
paths either — a name is a plain string, and the backend decides what it
means on its medium (ground rule #3).

Document filename, decided on #10 (1 Oct):

    YYYY-MM-DD <abbrev>[ — <qualifier>].<ext>

    2024-03-14 SOA.pdf
    2025-06-02 ROA — further advice.pdf

Date first so files sort chronologically inside an event folder. The short
name is the document type's `abbrev` in knowledge_base.json, and the only
qualifier today is the ROA situation, when the flag could propose one. Every
word in the name comes from the knowledge base or the document's date — never
from the uploaded filename, which is routinely the client's name.

No usable date means no proposed name, with the reason. A filename built on a
guessed date reorders a client's advice history the moment it is sorted.
"""

import json
from pathlib import PurePath

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_ABBREV = {doc["id"]: doc["abbrev"] for doc in _KB["documents"]}
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


def proposed_filename(
    doc_type: str | None,
    date_result: dict,
    flags: list[dict] | None = None,
    original_filename: str = "",
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

    # Only the extension is taken from the upload — never its stem.
    ext = PurePath(original_filename).suffix.lower() or ".pdf"
    return {"filename": name + ext, "reason": date_result["determination"]}
