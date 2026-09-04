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
from parser import parse_pdf
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
    result.update(check_scope(result["extracted_text"]))
    result["likely_type_name"] = _DOC_NAMES.get(result["likely_type"])
    if result["in_scope"]:
        result["classification"] = classify(result["extracted_text"])
        result["classification"]["doc_type_name"] = _DOC_NAMES.get(result["classification"].get("doc_type"))
    return result
