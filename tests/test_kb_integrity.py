"""Internal consistency of knowledge_base.json.

The knowledge base is the source of truth (CLAUDE.md rule #1), so a reference
in it to a document type that doesn't exist is a contradiction a developer has
to resolve by guessing. These tests make every machine-readable reference to a
document type resolve to an entry in `documents`.

Things a firm has that are NOT yet types (application forms, a general advice
warning) belong in `not_yet_document_types` as prose, where nothing mistakes
them for an id.
"""

import json

with open("knowledge_base.json") as f:
    KB = json.load(f)

DOC_IDS = {doc["id"] for doc in KB["documents"]}


def test_stage_map_names_only_real_document_types():
    for stage in KB["advice_process_stages"]:
        unknown = set(stage["typical_docs"]) - DOC_IDS
        assert not unknown, f"stage {stage['stage']} names {unknown}"


def test_advice_types_name_only_real_document_types():
    for advice_type in KB["advice_types"]:
        unknown = set(advice_type["documents"]) - DOC_IDS
        assert not unknown, f"{advice_type['id']} names {unknown}"


def test_every_link_has_the_same_shape_and_a_real_target():
    # One document once carried its links as prose strings while every other
    # carried {doc, relationship, note}. Code iterating links_to would crash on
    # that one entry, so the shape is asserted along with the target.
    for doc in KB["documents"]:
        for link in doc["links_to"]:
            assert isinstance(link, dict), f"{doc['id']} has a non-object link: {link!r}"
            assert set(link) == {"doc", "relationship", "note"}, doc["id"]
            assert link["doc"] in DOC_IDS, f"{doc['id']} links to {link['doc']}"
