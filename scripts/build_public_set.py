"""Read the public sample PDFs once with the real backend, for the demo screens.

    python scripts/build_public_set.py              # every PDF under samples/
    python scripts/build_public_set.py <folder> ...  # or just these folders

Every PDF under the folders goes through the same steps as /ingest. Each answer is
cached in samples/.results/ (git-ignored), so a rerun only reads new files. The
manifest is written to frontend/public-data.json as the "public" sample set the
React page shows next to the made-up one. Public documents only: published
examples, blank templates and provider forms. Never a firm's client files.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import ingest_bytes  # noqa: E402
from manifest import build_manifest  # noqa: E402

CACHE = ROOT / "samples" / ".results"
OUT = ROOT / "frontend" / "public-data.json"


def public_pdfs(folders: list[str]) -> list[Path]:
    """Every PDF under the given folders, except made-up ones in a `mock` folder."""
    return sorted(p for folder in folders for p in Path(folder).rglob("*.pdf")
                  if "mock" not in p.parts and ".results" not in p.parts)


def main(folders: list[str]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    pdfs = public_pdfs(folders)
    results = []
    for i, pdf in enumerate(pdfs, 1):
        cached = CACHE / (pdf.stem + ".json")
        if cached.exists():
            result = json.loads(cached.read_text())
        else:
            print(f"{i}/{len(pdfs)} reading {pdf.name}", flush=True)
            result = ingest_bytes(pdf.read_bytes(), pdf.name)
            cached.write_text(json.dumps(result, default=str))
        results.append(result)

    manifest = build_manifest(results)["local"]["default"]
    manifest.update({
        "dataset": "public",
        "dataset_label": "Public documents (real tool)",
        "dataset_note": "Published ASIC examples, blank templates and provider forms, read by the "
                        "real backend. No client data. Grouping into advice events isn't built yet, "
                        "so most documents show 'not placed yet'.",
    })
    OUT.write_text(json.dumps({"public": {"default": manifest}}, ensure_ascii=False, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(results)} documents")


if __name__ == "__main__":
    main(sys.argv[1:] or [str(ROOT / "samples")])
