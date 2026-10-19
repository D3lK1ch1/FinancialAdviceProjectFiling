"""Its presence puts the project root on sys.path, so `tests/*.py` can
`import parser`, `scope_gate`, `classifier`, `app` without a package/src layout.

It also gates the tests that need real sample documents. `samples/` is
gitignored on purpose — client- and collaborator-sourced documents are not
cleared for the repo — so a fresh clone has no PDFs. A test that reads them
carries `@pytest.mark.samples`; with no PDFs on disk it is skipped with a
reason, instead of failing with FileNotFoundError, which reads as a broken
change when it is really a missing input. Every unmarked test runs on a bare
clone.
"""

from pathlib import Path

import pytest

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"

_SKIP_NO_SAMPLES = pytest.mark.skip(
    reason="samples/ has no PDFs - it is gitignored (client documents never "
    "enter git). Get the set from the maintainer; see README, "
    "'docs/ and samples/ - shared outside git'."
)


def pytest_collection_modifyitems(items):
    if any(SAMPLES_DIR.glob("*.pdf")):
        return
    for item in items:
        if item.get_closest_marker("samples"):
            # append=False: a test parametrized over an empty sample list already
            # carries pytest's own "got empty parameter set" skip, and the first
            # skip mark wins. Ours has to be ahead of it to be the reason shown.
            item.add_marker(_SKIP_NO_SAMPLES, append=False)
