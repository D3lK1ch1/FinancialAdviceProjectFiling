"""
API layer — Phase 1: /ingest only. Nothing is persisted; each request parses
and returns the result in-memory. No classifier/filing/flagging yet.
"""

import hashlib
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from classifier import classify, engine_identity, engine_version
from clients import choose_client, find_client_candidates
from filing import proposed_filing
from display import DEFAULT_DISPLAY_MODE, DISPLAY_MODES, teaching_for
from confidence import verify
from flags import evaluate_flags
from kb import KB as _KB
from manifest import build_manifest
from parser import parse_pdf
from review import CorrectionRejected, assess, record_correction
from scope_gate import check_scope

app = FastAPI(title="Advice Document Filing — POC")
app.mount("/static", StaticFiles(directory="static"), name="static")

_DOC_NAMES = {doc["id"]: doc["name"] for doc in _KB["documents"]}


@app.get("/")
def root():
    return FileResponse("static/index.html")


# The React page (frontend/). `npm run build` writes frontend/dist/app/index.html
# with no data in it, so the page asks for files and calls /api/batch.
# check_dir=False: the app still starts when the front end isn't built; /app/
# is then a 404 (frontend/README.md says how to build it). static/index.html
# stays at / until the React page has Edit, failure-log verdicts and display
# mode.
app.mount("/app", StaticFiles(directory="frontend/dist/app", html=True, check_dir=False), name="app")


@app.post("/api/batch")
async def batch(files: list[UploadFile], display: str = DEFAULT_DISPLAY_MODE):
    """Several documents through /ingest's pipeline, as the manifest the React page reads.

    Proposals only, like /ingest: nothing is written.
    """
    _check_display(display)
    return build_manifest([ingest_bytes(await f.read(), f.filename, display) for f in files])


@app.post("/ingest")
async def ingest(file: UploadFile, display: str = DEFAULT_DISPLAY_MODE):
    _check_display(display)
    return ingest_bytes(await file.read(), file.filename, display)


def _check_display(display: str) -> None:
    if display not in DISPLAY_MODES:
        raise HTTPException(status_code=422, detail=f"display must be one of {sorted(DISPLAY_MODES)}")


def ingest_bytes(contents: bytes, filename: str, display: str = DEFAULT_DISPLAY_MODE) -> dict:
    """One document through the whole pipeline. /ingest and /api/batch both use it."""
    result = parse_pdf(BytesIO(contents), filename)
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
    # Which engine produced this result (#7). Read per document, and always
    # present: an out-of-scope answer came from the knowledge base's title
    # patterns, and a reviewer's verdict on it is measured against them. The
    # page sends this back with the verdict, so the failure log records the
    # engine that made the proposal, not whatever is running when someone clicks.
    identity = engine_identity()
    result["engine_version"] = engine_version(identity)
    if "identity_error" in identity:
        result["engine_version_error"] = identity["identity_error"]
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
    # always present, empty when nothing is labelled — same reason as flags.
    result["client_candidates"] = find_client_candidates(pages)
    # The one client they agree on, or none with the reason. Deliberately not
    # passed to assess() below: a person confirms the client on every document
    # (review_policy.certainty_decision), so a proposed client must not make a
    # document look safer to file. More than one client raises ambiguous_client.
    result["client"] = choose_client(result["client_candidates"])
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
    result["filing"] = proposed_filing(
        doc_type, result["extracted_text"], pages, result["flags"], filename, client=result["client"]
    )
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
    engine_version: dict | None = None


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
