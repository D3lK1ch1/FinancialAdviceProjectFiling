"""scripts/accuracy_report.py scores right answers, and counts the dangerous misses."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from accuracy_report import score  # noqa: E402


def _result(doc_type, held, code=None):
    return {"classification": {"doc_type": doc_type, "confidence": 0.95},
            "review": {"needs_review": held, "reasons": [{"code": code}] if code else []}}


def test_right_held_and_the_dangerous_miss_are_told_apart():
    labels = {"a.pdf": "soa", "b.pdf": "soa", "c.pdf": "pds", "form.pdf": "implementation_form"}
    results = {"a": _result("soa", False), "b": _result(None, True, "out_of_scope"),
               "c": _result("soa", False), "form": _result("pds", False)}
    rows = score(results, labels)
    by = {r["name"]: r for r in rows["known"] + rows["not_yet"]}

    assert by["a.pdf"]["right"] and not by["a.pdf"]["wrong_and_unheld"]
    assert not by["b.pdf"]["right"] and by["b.pdf"]["why"] == "out_of_scope"
    assert by["c.pdf"]["wrong_and_unheld"] and by["c.pdf"]["why"] == "lookalike"
    assert by["form.pdf"]["wrong_and_unheld"]          # scored separately, still counted
    assert [r["name"] for r in rows["not_yet"]] == ["form.pdf"]


def test_unread_documents_are_left_out_not_counted_wrong():
    assert score({}, {"a.pdf": "soa"}) == {"known": [], "not_yet": []}
