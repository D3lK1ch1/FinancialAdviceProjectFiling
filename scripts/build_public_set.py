"""Read the public sample PDFs once with the real backend, for the accuracy report.

    python scripts/build_public_set.py              # every PDF under samples/
    python scripts/build_public_set.py <folder> ...  # or just these folders

Every PDF under the folders goes through the same steps as /ingest. Each answer is
cached in samples/.results/ (git-ignored), so a rerun only reads new files, and
scripts/accuracy_report.py scores the cache. Public documents only: published
examples, blank templates and provider forms. Never a firm's client files.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import ingest_bytes  # noqa: E402

CACHE = ROOT / "samples" / ".results"


def public_pdfs(folders: list[str]) -> list[Path]:
    """Every PDF under the given folders, except made-up ones in a `mock` folder."""
    return sorted(p for folder in folders for p in Path(folder).rglob("*.pdf")
                  if "mock" not in p.parts and ".results" not in p.parts)


def main(folders: list[str]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    pdfs = public_pdfs(folders)
    for i, pdf in enumerate(pdfs, 1):
        cached = CACHE / (pdf.stem + ".json")
        if not cached.exists():
            print(f"{i}/{len(pdfs)} reading {pdf.name}", flush=True)
            cached.write_text(json.dumps(ingest_bytes(pdf.read_bytes(), pdf.name), default=str))
    print(f"{len(pdfs)} documents cached in {CACHE.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:] or [str(ROOT / "samples")])
