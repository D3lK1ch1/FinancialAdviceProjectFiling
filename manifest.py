"""
The batch manifest the React page reads (frontend/README.md).

Reshapes /ingest results; decides nothing. Every type, threshold, flag and
folder comes from the result, which got it from the knowledge base. The one
thing done here that /ingest does not do is collect results into a batch.

A path is only joined when every part of it is known: a path with a hole in it
reads as a real destination (filing.proposed_filing). The page shows the
missing part and its reason instead.
"""

import hashlib
import re

from kb import KB as _KB

_DOCS = {doc["id"]: doc for doc in _KB["documents"]}
_POLICY = _KB["review_policy"]
_EVENT_FOLDER = re.compile(r"^(\d{4}-\d{2})\W*(.*)$")


def build_manifest(results: list[dict]) -> dict:
    """{"local": {"default": manifest}}, the shape `window.DATA` has in the demo."""
    documents, events = [], {}
    for result in results:
        doc = _document(result)
        documents.append(doc)
        event = _event(result, doc)
        if event:
            events.setdefault(event["event_id"], event)
            doc["event_id"] = event["event_id"]
    held = sum(1 for d in documents if d["needs_review"])
    manifest = {
        "dataset": "local",
        "dataset_label": "Your documents",
        "dataset_note": None,
        "filing_profile": "default",
        "profile_name": "Client, then advice event",
        "profile_description": "The filing this backend proposes today. Step folders (#70) are not built yet.",
        "knowledge_base_version": _KB["meta"].get("version"),
        "confidence_threshold": _POLICY["default_threshold"],
        "batch": {"documents": len(documents), "needs_review": held, "auto_filed": len(documents) - held},
        "events": list(events.values()),
        "documents": documents,
    }
    return {"local": {"default": manifest}}


def _document(result: dict) -> dict:
    classification = result.get("classification") or {}
    doc_type = classification.get("doc_type")
    entry = _DOCS.get(doc_type, {})
    review = result.get("review") or {}
    filing = result.get("filing") or {}
    return {
        "doc_id": result["document_id"][:16],
        "source_name": result.get("filename") or "document.pdf",
        "type": doc_type,
        "type_label": entry.get("abbrev") or "UNKNOWN",
        "category": entry.get("category"),
        "confidence": classification.get("confidence") or 0.0,
        "classification_evidence": "; ".join(classification.get("matched_signals") or []) or None,
        "extraction_quality": None,                     # not scored by this backend yet
        "pages": result.get("page_count") or 0,
        "client": filing.get("client_folder"),
        "client_provenance": filing.get("client_reason"),
        "date": filing.get("date"),
        "date_provenance": filing.get("date_determination"),
        "event_id": None,
        "attachment_reason": filing.get("event_reason"),
        "needs_review": bool(review.get("needs_review")),
        "review_reasons": [r.get("why") for r in review.get("reasons") or [] if r.get("why")],
        "threshold": review.get("threshold"),
        "flags": [_flag(f) for f in result.get("flags") or []],
        "stages": filing.get("stages") or [],
        "destination": _destination(review, filing),
    }


def _flag(flag: dict) -> dict:
    return {
        "id": flag["id"],
        "severity": flag.get("severity"),
        "message": flag.get("message") or flag.get("why") or "",
        "blocks_filing": bool(flag.get("forces_review")),
    }


def _destination(review: dict, filing: dict) -> dict:
    filename = filing.get("filename")
    if review.get("needs_review"):
        folder = [review.get("destination") or _POLICY["destination"]]
        rationale = "held for a person"
    else:
        folder = [p for p in (filing.get("client_folder"), filing.get("event_folder")) if p]
        missing = [reason for part, reason in (
            (filing.get("client_folder"), filing.get("client_reason")),
            (filing.get("event_folder"), filing.get("event_reason")),
        ) if not part]
        rationale = "; ".join(r for r in missing if r) or filing.get("event_reason")
        if missing:
            return {"folder": folder, "filename": filename, "path": None, "rationale": rationale}
    path = "/".join(folder + [filename]) if filename else None
    return {"folder": folder, "filename": filename, "path": path, "rationale": rationale}


def _event(result: dict, doc: dict) -> dict | None:
    """An advice record that names its event folder opens that event (#8 for the rest)."""
    folder = (result.get("filing") or {}).get("event_folder")
    if not folder:
        return None
    match = _EVENT_FOLDER.match(folder)
    key = f"{doc['client']}|{folder}"
    return {
        "event_id": "evt-" + hashlib.sha256(key.encode()).hexdigest()[:10],
        "client": doc["client"],
        "subject": match.group(2) if match else folder,
        "date": match.group(1) if match else None,
        "record_label": doc["type_label"],
        "sub_kind": None,
    }
