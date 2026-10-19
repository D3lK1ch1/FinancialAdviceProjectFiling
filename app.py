"""
API layer — Phase 1: /ingest only. Nothing is persisted; each request parses
and returns the result in-memory. No classifier/filing/flagging yet.
"""

import hashlib
import json
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from classifier import classify
from clients import find_client_candidates
from filing import proposed_filing
from display import DEFAULT_DISPLAY_MODE, DISPLAY_MODES, teaching_for
from confidence import verify
from flags import evaluate_flags
from parser import parse_pdf
from review import CorrectionRejected, assess, record_correction
from scope_gate import check_scope

app = FastAPI(title="Advice Document Filing — POC")
app.mount("/static", StaticFiles(directory="static"), name="static")

# UTF-8 stated, not left to the platform: Windows defaults to cp1252, which
# garbled every em dash and curly quote in the knowledge base on the way to
# the screen.
with open("knowledge_base.json", encoding="utf-8") as f:
    _KB = json.load(f)

_DOC_NAMES = {doc["id"]: doc["name"] for doc in _KB["documents"]}


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.post("/ingest")
async def ingest(file: UploadFile, display: str = DEFAULT_DISPLAY_MODE):
    if display not in DISPLAY_MODES:
        raise HTTPException(status_code=422, detail=f"display must be one of {sorted(DISPLAY_MODES)}")
    contents = await file.read()
    result = parse_pdf(BytesIO(contents), file.filename)
    # The identity a reviewer's correction is recorded against. A hash of the
    # bytes rather than the filename, which is routinely the client's name —
    # see the de-identification rule in failure_log.py.
    result["document_id"] = hashlib.sha256(contents).hexdigest()
    # Per-page text is for server-side work (bundle detection — see the
    # multi_doc_bundle rule in knowledge_base.json). It is not part of the
    # response: echoing it alongside extracted_text would roughly double the
    # payload for a consumer that does not exist yet. The PR that consumes it
    # can decide whether the API should expose it.
    # Kept locally for bundle detection and dropped from the response: echoing
    # per-page text alongside extracted_text would roughly double the payload
    # for a consumer that does not exist yet.
    pages = result.pop("pages")
    result.update(check_scope(result["extracted_text"]))
    result["likely_type_name"] = _DOC_NAMES.get(result["likely_type"])
    doc_type = None
    if result["in_scope"]:
        # The model's own confidence is a claim about itself. Check the
        # phrases it says it matched, and compare its answer against the scope
        # gate's independent read, BEFORE anything acts on the number — the
        # review threshold below is applied to the verified figure, not the
        # reported one. The model's original number survives as
        # confidence_raw.
        result["classification"] = verify(
            classify(result["extracted_text"]),
            result["extracted_text"],
            result["likely_type"],
        )
        result["classification"]["doc_type_name"] = _DOC_NAMES.get(result["classification"].get("doc_type"))
        doc_type = result["classification"].get("doc_type")
    # Always present, even when nothing fired and even out of scope — a
    # missing key and an empty list read the same to a caller that has to
    # branch on both, and "no flags" is a result worth stating.
    #
    # Keyed on the CLASSIFIED type, not the scope gate's likely_type: the gate
    # matches a title pattern, so a document that merely mentions an ROA would
    # otherwise be asked which legislative basis it is.
    result["flags"] = evaluate_flags(doc_type, result["extracted_text"], pages)
    # Whose document it is, as the document itself says (#6). Every name found,
    # none chosen yet, and deliberately not passed to assess() below: until
    # one is selected, a found name must not make a document look safer to
    # file. Always present, empty when nothing is labelled — same reason as flags.
    result["client_candidates"] = find_client_candidates(pages)
    # Whether this can stand on its own, and why not if it can't. Out of scope
    # is a review reason here rather than the end of the road: the document
    # keeps its working either way, because a reviewer confirming a correct
    # low-confidence answer is the failure-log evidence ground rule #6 wants.
    result["review"] = assess(
        in_scope=result["in_scope"],
        classification=result.get("classification"),
        flags=result["flags"],
        parse_error=result.get("parse_error"),
        has_selectable_text=result["has_selectable_text"],
    )
    # Where it would be filed (#10). A proposal only: nothing is written, and
    # the client folder stays empty until a client is chosen (GH#6).
    result["filing"] = proposed_filing(doc_type, result["extracted_text"], pages, result["flags"], file.filename)
    # Display mode (#11). Added last and from the classified type only, so it
    # cannot reach back into anything above — the settings independence rule.
    result["teaching"] = teaching_for(doc_type, display)
    return result


class Correction(BaseModel):
    document_id: str
    predicted_type: str | None
    correct_type: str
    reason: str
    corrections: list[dict] = []


@app.post("/review/correction", status_code=201)
def review_correction(correction: Correction):
    """A reviewer's verdict on one document, written to the failure log.

    What the Approve/Edit/Reject screen calls (#4). It records a judgement and
    files nothing — filing is #10.
    """
    try:
        record_correction(**correction.model_dump())
    except CorrectionRejected as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"recorded": True, "document_id": correction.document_id}


@app.get("/review/options")
def review_options():
    """The choices the review screen offers, read from the knowledge base.

    The page must not keep its own copy of the document types or the reasons
    (ground rule #1): a type added to the knowledge base appears on the screen
    with no change to the page. Approve sends `confirmed`; a reject picks one
    of the others. Every reason is a fixed code — there is no free-text "why",
    because that box is where a client's name gets typed (see
    review_policy.correction_reasons).
    """
    codes = _KB["review_policy"]["correction_reasons"]["codes"]
    return {
        "document_types": [{"id": doc["id"], "name": doc["name"]} for doc in _KB["documents"]],
        "approve_reason": "confirmed",
        "reject_reasons": [
            {"code": code, "meaning": meaning}
            for code, meaning in codes.items()
            if code != "confirmed"
        ],
    }
