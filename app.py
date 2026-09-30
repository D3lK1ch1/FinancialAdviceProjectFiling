"""
API layer — Phase 1: /ingest only. Nothing is persisted; each request parses
and returns the result in-memory. No classifier/filing/flagging yet.
"""

import json
from io import BytesIO

from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from classifier import classify
from flags import evaluate_flags
from parser import parse_pdf
from review import assess
from scope_gate import check_scope

app = FastAPI(title="Advice Document Filing — POC")
app.mount("/static", StaticFiles(directory="static"), name="static")

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_DOC_NAMES = {doc["id"]: doc["name"] for doc in _KB["documents"]}


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.post("/ingest")
async def ingest(file: UploadFile):
    contents = await file.read()
    result = parse_pdf(BytesIO(contents), file.filename)
    # Per-page text is for server-side work (bundle detection — see the
    # multi_doc_bundle rule in knowledge_base.json). It is not part of the
    # response: echoing it alongside extracted_text would roughly double the
    # payload for a consumer that does not exist yet. The PR that consumes it
    # can decide whether the API should expose it.
    result.pop("pages")
    result.update(check_scope(result["extracted_text"]))
    result["likely_type_name"] = _DOC_NAMES.get(result["likely_type"])
    doc_type = None
    if result["in_scope"]:
        result["classification"] = classify(result["extracted_text"])
        result["classification"]["doc_type_name"] = _DOC_NAMES.get(result["classification"].get("doc_type"))
        doc_type = result["classification"].get("doc_type")
    # Always present, even when nothing fired and even out of scope — a
    # missing key and an empty list read the same to a caller that has to
    # branch on both, and "no flags" is a result worth stating.
    #
    # Keyed on the CLASSIFIED type, not the scope gate's likely_type: the gate
    # matches a title pattern, so a document that merely mentions an ROA would
    # otherwise be asked which legislative basis it is.
    result["flags"] = evaluate_flags(doc_type, result["extracted_text"])
    # Whether this can stand on its own, and why not if it can't. Out of scope
    # is a review reason here rather than the end of the road: the document
    # keeps its working either way, because a reviewer confirming a correct
    # low-confidence answer is the failure-log evidence ground rule #6 wants.
    result["review"] = assess(
        in_scope=result["in_scope"],
        classification=result.get("classification"),
        flags=result["flags"],
    )
    return result
