"""The knowledge base, loaded once

Every module that reads `knowledge_base.json` imports `KB` from here instead of
opening the file itself. Before this, nine modules each opened it by a path
relative to the working directory, so the app broke when started from any
other folder, and five of them read it without stating UTF-8 — on Windows that
is cp1252, which garbled every em dash and curly quote, including the ones in
the classifier hints sent to the model.

The path is resolved from this file, not the working directory. The shape is
checked at import, so a knowledge base missing a section fails here with the
section's name, not later as a KeyError in whichever module reads it first.
"""

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "knowledge_base.json"

# Every top-level section some module reads. `meta` carries the version that
# results will be stamped with.
REQUIRED_SECTIONS = (
    "meta",
    "documents",
    "advice_process_stages",
    "client_model",
    "confidence_policy",
    "edge_case_flags",
    "filing_model",
    "review_policy",
    "settings",
)


class KnowledgeBaseError(Exception):
    pass


def load(path: Path = PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        kb = json.load(f)
    missing = [section for section in REQUIRED_SECTIONS if section not in kb]
    if missing:
        raise KnowledgeBaseError(f"{path} is missing required section(s): {', '.join(missing)}")
    if not isinstance(kb["meta"].get("version"), str):
        raise KnowledgeBaseError(f"{path} has no meta.version string")
    return kb


KB = load()
