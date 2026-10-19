"""Display mode — teach, or don't (#11, ground rule #4).

The teaching text is the knowledge base's own `teaching` block per document
type, written for staff new to the industry. It is read from there and never
copied into code: `meta.consumers` names the teaching layer as one of the
three things each document entry feeds, from a single source of truth.

Display is the outermost layer. It reads a result's document type and adds
text beside it; it never reads or changes the classification, the flags or
the review decision. tests/test_settings.py holds that line.
"""

import json

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_SETTING = _KB["settings"]["display_mode"]
_DOCS = {doc["id"]: doc for doc in _KB["documents"]}

DISPLAY_MODES = set(_SETTING["options"])
DEFAULT_DISPLAY_MODE = _SETTING["value"]


def teaching_for(doc_type: str | None, mode: str = DEFAULT_DISPLAY_MODE) -> dict | None:
    """The teaching note for a document type, or None when there is nothing to teach.

    None when display is off, and when the document has no type — a note
    about the wrong type would teach the wrong thing.
    """
    if mode not in DISPLAY_MODES:
        raise ValueError(f"unknown display mode {mode!r}; known modes are {sorted(DISPLAY_MODES)}")
    if mode != "teach" or doc_type not in _DOCS:
        return None
    doc = _DOCS[doc_type]
    return {"doc_type": doc_type, "name": doc["name"], **doc["teaching"]}
