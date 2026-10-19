"""
GET /review/options — the choices the review screen offers. Each test checks
the response against knowledge_base.json, so the screen can never drift from
the knowledge base it is meant to read.
"""

import json

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

with open("knowledge_base.json", encoding="utf-8") as f:
    _KB = json.load(f)

_CODES = _KB["review_policy"]["correction_reasons"]["codes"]


def _options() -> dict:
    response = client.get("/review/options")
    assert response.status_code == 200
    return response.json()


def test_offers_every_document_type_in_the_knowledge_base():
    assert _options()["document_types"] == [
        {"id": doc["id"], "name": doc["name"]} for doc in _KB["documents"]
    ]


def test_approve_sends_confirmed():
    assert _options()["approve_reason"] == "confirmed"
    assert "confirmed" in _CODES


def test_reject_offers_every_other_reason_with_its_meaning():
    reject = _options()["reject_reasons"]
    assert [r["code"] for r in reject] == [c for c in _CODES if c != "confirmed"]
    assert all(r["meaning"] == _CODES[r["code"]] for r in reject)


def test_confirmed_is_not_a_reject_reason():
    """'Confirmed' means the tool was right. Offering it on a reject would let
    a reviewer record both at once."""
    assert "confirmed" not in {r["code"] for r in _options()["reject_reasons"]}


def test_every_choice_is_one_the_correction_endpoint_accepts():
    """What the screen offers and what /review/correction accepts must be the
    same lists, or a reviewer could pick something the server refuses."""
    from review import _CORRECTION_REASONS, _DOC_IDS

    options = _options()
    assert {t["id"] for t in options["document_types"]} == _DOC_IDS
    offered = {options["approve_reason"]} | {r["code"] for r in options["reject_reasons"]}
    assert offered == set(_CORRECTION_REASONS)
