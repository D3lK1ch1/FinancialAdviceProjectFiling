"""The three settings stay independent (#11, CLAUDE.md ground rule #4).

Display mode is the only one with behaviour so far. Filing mode and the
classification engine are declared in knowledge_base.json and get their own
independence tests when they gain behaviour (#10, #3).

No samples/ and no Ollama: the PDF is generated in memory and the model call
is replaced with a fixed answer, so every run is identical.
"""

import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

import app as app_module
from display import teaching_for

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_SETTINGS = _KB["settings"]
_DOCS = {doc["id"]: doc for doc in _KB["documents"]}

client = TestClient(app_module.app)


def _pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=300)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 20 250 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def fixed_classifier(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "classify",
        lambda text: {"doc_type": "risk_profile", "confidence": 0.95, "matched_signals": ["Risk Profile"]},
    )


def _ingest(display=None):
    params = {} if display is None else {"display": display}
    pdf = _pdf("Risk Profile Questionnaire")
    res = client.post("/ingest", params=params, files={"file": ("rp.pdf", pdf, "application/pdf")})
    assert res.status_code == 200, res.text
    return res.json()


# --- The settings themselves --------------------------------------------------


@pytest.mark.parametrize("name", ["display_mode", "filing_mode", "classification_engine"])
def test_each_setting_is_declared_in_the_kb_with_a_valid_value(name):
    setting = _SETTINGS[name]

    assert setting["value"] in setting["options"]
    assert isinstance(setting["implemented"], bool)


def test_a_setting_without_behaviour_says_so():
    """Nothing that does nothing may look live."""
    assert _SETTINGS["display_mode"]["implemented"] is True
    assert _SETTINGS["filing_mode"]["implemented"] is False
    assert _SETTINGS["classification_engine"]["implemented"] is False


# --- Display mode -------------------------------------------------------------


@pytest.mark.parametrize("doc_type", list(_DOCS))
def test_teach_mode_reads_the_kb_teaching_block_for_every_type(doc_type):
    note = teaching_for(doc_type, "teach")

    for key, text in _DOCS[doc_type]["teaching"].items():
        assert note[key] == text
    assert note["name"] == _DOCS[doc_type]["name"]


def test_off_and_untyped_give_no_teaching():
    assert teaching_for("soa", "off") is None
    assert teaching_for(None, "teach") is None


def test_an_unknown_display_mode_is_refused():
    with pytest.raises(ValueError):
        teaching_for("soa", "verbose")
    res = client.post("/ingest", params={"display": "verbose"},
                      files={"file": ("x.pdf", _pdf("Risk Profile"), "application/pdf")})
    assert res.status_code == 422


def test_ingest_teaches_by_default(fixed_classifier):
    result = _ingest()

    assert _SETTINGS["display_mode"]["value"] == "teach"
    assert result["teaching"]["doc_type"] == "risk_profile"
    assert result["teaching"]["why_it_exists"] == _DOCS["risk_profile"]["teaching"]["why_it_exists"]


def test_display_mode_changes_nothing_but_the_teaching(fixed_classifier):
    """Ground rule #4 for display mode: switching it leaves classification,
    confidence, flags and the review decision byte-identical."""
    taught = _ingest("teach")
    plain = _ingest("off")

    assert taught["teaching"] is not None
    assert plain["teaching"] is None

    taught.pop("teaching")
    plain.pop("teaching")
    assert json.dumps(taught, sort_keys=True) == json.dumps(plain, sort_keys=True)
