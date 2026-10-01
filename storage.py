"""Storage seam — the one place filing touches a disk (#10, ground rule #3).

Filing has to move from a local folder to an Australian-region cloud bucket
later (build step 6) without the classifier changing. So nothing outside this
module knows what a path separator, a root folder or a bucket is. Callers hand
over a destination as a list of plain segments —

    ["_Needs review", "2024-03 — Retirement [SOA]", "2024-03-14 SOA.pdf"]

— and the backend decides what that means on its medium. tests/test_storage.py
asserts that classifier.py, scope_gate.py and app.py carry no file-system
imports, so the seam cannot erode quietly.

Nothing here is called on ingest. `proposed_path` describes where a document
WOULD go; `put` runs only after a person approves (ground rule #2), and that
approve step does not exist yet. `put` refuses to overwrite: a second document
landing on an existing name is a question for a person, not a silent replace
of a client record.
"""

import re
from pathlib import Path
from typing import Protocol

# Characters no common filesystem or bucket key accepts in a name, plus the
# separators themselves. A segment comes from document content — a subject
# area, a product name — and "Super/Pension" must not become two folders.
_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_segment(segment: str) -> str:
    """One folder or file name, safe on any backend.

    Unsafe characters become "-". A segment that is empty, or only dots,
    after cleaning is refused rather than repaired: "" or ".." as a folder
    name is not a near-miss, it is a path that points somewhere else.
    """
    cleaned = _UNSAFE.sub("-", segment).strip().rstrip(".")
    if not cleaned or set(cleaned) == {"."}:
        raise ValueError(f"not a usable folder or file name: {segment!r}")
    return cleaned


class Storage(Protocol):
    def proposed_path(self, segments: list[str]) -> str:
        """Where a document would go, as this backend would show it. No side effects."""

    def exists(self, segments: list[str]) -> bool:
        """Whether something already sits at that destination."""

    def put(self, data: bytes, segments: list[str]) -> str:
        """Write after approval. Raises FileExistsError rather than overwrite."""


class LocalStorage:
    """A folder on the firm's own machine — the only backend this phase needs."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _resolve(self, segments: list[str]) -> Path:
        if not segments:
            raise ValueError("a destination needs at least a file name")
        path = self.root.joinpath(*(clean_segment(s) for s in segments)).resolve()
        # clean_segment already removes separators and dot-only names, so this
        # cannot fire today. It stays because it is the property that matters:
        # nothing this backend writes may land outside its root.
        if not path.is_relative_to(self.root):
            raise ValueError("destination escapes the filing root")
        return path

    def proposed_path(self, segments: list[str]) -> str:
        return str(self._resolve(segments))

    def exists(self, segments: list[str]) -> bool:
        return self._resolve(segments).exists()

    def put(self, data: bytes, segments: list[str]) -> str:
        path = self._resolve(segments)
        path.parent.mkdir(parents=True, exist_ok=True)
        # "x" mode: create, and fail if the name is taken. Checking exists()
        # first and then writing would leave a gap for a second write to land in.
        with open(path, "xb") as f:
            f.write(data)
        return str(path)
