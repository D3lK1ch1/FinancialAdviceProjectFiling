"""Tests for storage.py — the filing seam (#10, ground rule #3).

Everything writes under pytest's tmp_path; no samples/ needed.
"""

import ast
from pathlib import Path

import pytest

from storage import LocalStorage, Storage, clean_segment

ROOT = Path(__file__).resolve().parent.parent

EVENT = ["Client A", "2024-03 — Retirement & Super Consolidation", "2024-03-14 SOA.pdf"]


def test_local_storage_satisfies_the_interface():
    store: Storage = LocalStorage("/tmp")
    assert all(callable(getattr(store, m)) for m in ("proposed_path", "exists", "put"))


def test_proposed_path_describes_without_writing(tmp_path):
    store = LocalStorage(tmp_path)

    path = store.proposed_path(EVENT)

    assert path == str(tmp_path.resolve().joinpath(*EVENT))
    assert not any(tmp_path.iterdir()), "proposing must not create anything"


def test_put_writes_creating_folders(tmp_path):
    store = LocalStorage(tmp_path)

    written = store.put(b"%PDF-", EVENT)

    assert Path(written).read_bytes() == b"%PDF-"
    assert store.exists(EVENT)


def test_put_never_overwrites(tmp_path):
    """A second document on an existing name is a question for a person, not
    a silent replace of a client record."""
    store = LocalStorage(tmp_path)
    store.put(b"first", EVENT)

    with pytest.raises(FileExistsError):
        store.put(b"second", EVENT)
    assert Path(store.proposed_path(EVENT)).read_bytes() == b"first"


@pytest.mark.parametrize(
    "segment, cleaned",
    [
        ("Super/Pension", "Super-Pension"),
        ("Super\\Pension", "Super-Pension"),
        ('PDS — "Growth" fund?', "PDS — -Growth- fund-"),
        ("  2024-03-14 SOA.pdf  ", "2024-03-14 SOA.pdf"),
        ("Trailing dot.", "Trailing dot"),
    ],
)
def test_a_segment_from_document_content_stays_one_segment(segment, cleaned):
    assert clean_segment(segment) == cleaned


@pytest.mark.parametrize("segment", ["", "   ", ".", "..", "..."])
def test_an_unusable_segment_is_refused_not_repaired(segment):
    with pytest.raises(ValueError):
        clean_segment(segment)


def test_nothing_lands_outside_the_root(tmp_path):
    store = LocalStorage(tmp_path / "filing")

    with pytest.raises(ValueError):
        store.proposed_path(["..", "..", "etc", "passwd"])
    path = store.proposed_path(["../escape.pdf"])
    assert Path(path).parent == (tmp_path / "filing").resolve()


def test_an_empty_destination_is_refused(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).proposed_path([])


# --- The seam itself ---------------------------------------------------------

_FILESYSTEM_MODULES = {"os", "pathlib", "shutil", "storage", "boto3", "google", "azure"}


@pytest.mark.parametrize("module", ["classifier.py", "scope_gate.py", "app.py"])
def test_classification_code_carries_no_storage_detail(module):
    """#10 box 4. If classification code imports a file-system or bucket
    library, the swap from local folder to cloud stops being a backend change.
    Filing will reach app.py through a call into storage.py's interface, and
    this test is updated deliberately when it does — not drifted past."""
    tree = ast.parse((ROOT / module).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert not imported & _FILESYSTEM_MODULES, f"{module} imports {imported & _FILESYSTEM_MODULES}"
