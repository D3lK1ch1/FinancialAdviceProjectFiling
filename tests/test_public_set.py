"""scripts/build_public_set.py takes only the PDFs it is pointed at, never mocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_public_set import public_pdfs  # noqa: E402


def test_only_pdfs_under_the_given_folders_and_never_mocks(tmp_path):
    (tmp_path / "soa").mkdir()
    (tmp_path / "mock").mkdir()
    (tmp_path / "soa" / "asic-soa.pdf").write_bytes(b"%PDF")
    (tmp_path / "soa" / "notes.txt").write_text("not a pdf")
    (tmp_path / "mock" / "made-up.pdf").write_bytes(b"%PDF")
    elsewhere = tmp_path.parent / "elsewhere.pdf"
    elsewhere.write_bytes(b"%PDF")

    assert [p.name for p in public_pdfs([str(tmp_path)])] == ["asic-soa.pdf"]
