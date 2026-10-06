# Advice Document Classifier & Filing System
Classifies and files financial-advice documents for Australian advice firms.

A public demonstration of where the pipeline and review UI are heading:
**https://advice-document-classifier.vercel.app**, built from
[`ahaythorpe/advice-document-classifier`](https://github.com/ahaythorpe/advice-document-classifier)

The purpose of this project is to build upon the referred public demo from pilot stage to an actual product.

> **`docs/` and `samples/` are not in this git repo.** They're gitignored on purpose since planning docs and sample documents are client/collaborator-sourced material, not cleared for public repo (in discussion). A fresh clone will build and pass most tests but won't have them.

## Run it

Works on **macOS and Windows**. Where the commands differ, both are shown. On a
Mac, use the **Terminal** app; on Windows, **PowerShell**.

**What you need first**
- **Python 3.10 or newer.** Check with `python3 --version` (Mac) or `python --version`
  (Windows). On a Mac, install it from [python.org](https://www.python.org/downloads/)
  if the version is older or missing.
- **[Ollama](https://ollama.com/download)**, which runs the AI model on your own
  computer. Install it like any app. On a Mac it lives in the menu bar (top right);
  on Windows, in the system tray (bottom right).
- **The `samples/` folder**, from Delia directly (it is not in git, see below).

**One-time setup**

1. Get the code and go into its folder:
   ```
   git clone https://github.com/D3lK1ch1/FinancialAdviceProjectFiling.git
   cd FinancialAdviceProjectFiling
   ```
   On a Mac, the first `git` command may offer to install "command line developer
   tools". Accept, wait for it to finish, then run the command again. Put the
   `samples/` folder from Delia inside this project folder.
2. Make a private Python environment for the project, so nothing clashes with
   anything else on your computer:

   | Mac | Windows |
   |---|---|
   | `python3 -m venv .venv` | `python -m venv .venv` |
   | `source .venv/bin/activate` | `.venv\Scripts\activate` |

   Your prompt now starts with `(.venv)`. From here on, **`python` works the same
   on both**.
3. Install what the app needs:
   ```
   python -m pip install -r requirements.txt
   ```
4. Download the AI model (about 5 GB, once):
   ```
   ollama pull llama3.1
   ```

**Every time you use it**

1. **Start Ollama** (open the Ollama app), then open
   **http://localhost:11434** in your browser. It must say **"Ollama is running"**.
2. In Terminal / PowerShell, inside the project folder:

   | Mac | Windows |
   |---|---|
   | `source .venv/bin/activate` | `.venv\Scripts\activate` |

   ```
   python -m uvicorn app:app --port 8000
   ```
3. Open **http://127.0.0.1:8000/** and drop a PDF on the page.
4. To stop: press `Ctrl+C` in Terminal / PowerShell (on a Mac too, it's `Ctrl`,
   not `Cmd`).

**If the card says "Couldn't reach the classifier … connection refused"**
(`WinError 10061` on Windows, `Errno 61` on a Mac), Ollama isn't running. It has
nothing to do with Wi-Fi: the app and Ollama talk to each other *inside* your
computer. Start Ollama, check http://localhost:11434 again, and drop the file
again. The first document after a few idle minutes can take a minute while the
model loads; that is normal.

## Reviewing a document

Every result card ends in **Your verdict**. Nothing is ever filed or moved — a
verdict is **recorded**, so the tool can be measured and improved.

- **Approve** — the tool named the document type correctly.
- **Reject** — it didn't. Choose **what it actually is** and **why** it was wrong:

  | reason | when to pick it |
  |---|---|
  | lookalike | it quotes, cites or resembles another type (an SOA that refers to a PDS) |
  | non standard title | its own title is missing, firm-branded or worded unusually |
  | poor text | the text was garbled or incomplete (a scan, an image-heavy page) |
  | bundle | one file holds more than one document |
  | knowledge base gap | none of the above: the tool is missing a rule |

  There is no free-text box on purpose: a typed note is where a client's name ends
  up. The full meaning of each reason shows on screen when you pick it.
- A document the tool couldn't place ("Not recognised") offers Reject only.

**Your verdicts are real data.** Each one is a line in `failure_log.jsonl` in the
project folder, recorded against a code made from the file's contents — never the
file name. They are how the 90% review level gets checked against reality. When
you've finished a review session, **send `failure_log.jsonl` to Delia.**

Ollama is used for the purposes of this project, but API keys from LLMs such as Anhropic (Claude) and OpenAI (Codex) can be considered and built upon.

## Run the tests

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

`requirements-dev.txt` is `requirements.txt` plus `pytest` and `httpx`.

Use the `python -m pytest` form, not bare `pytest` — on Windows the bare
command depends on Python's `Scripts/` folder being on `PATH`, which isn't
guaranteed. `python -m pytest` always resolves to the same interpreter you
just used to run `python -m uvicorn` above.

Runs everything under `tests/`. Root `conftest.py` puts the project root on
`sys.path` so test files can `import parser`, `scope_gate`, `classifier`, `app`
directly — no package/src layout needed.

| test file | covers |
|---|---|
| `tests/test_parser.py` | `parse_pdf()` against all 10 real `samples/*.pdf` |
| `tests/test_scope_gate.py` | `check_scope()` against all 10 samples (correct type per filename prefix), the 2026-08-22 FSG/SOA cross-reference regression, and an out-of-scope text case |
| `tests/test_classifier.py` | `_parse_response()` (plain/fenced/malformed JSON) and `classify()` (success, missing optional fields, request exception, malformed JSON, missing `response` key) — `requests.post` mocked, no Ollama needed |
| `tests/test_e2e.py` | Full `POST /ingest` pipeline (parse → scope_gate → classify), one real sample per doc type, plus an out-of-scope (text-less) PDF. **Needs Ollama running with `llama3.1` pulled — hits it for real, not mocked.** On a misclassification, also writes a `failure_log.jsonl` entry |
| `tests/test_failure_log.py` | `log_failure()` appends correctly-shaped JSON Lines records; handles `None` predicted type; appends without overwriting; the record carries **only** the five de-identified fields, and `logged_at` is UTC |

**On a bare clone** (no `samples/`, no `docs/`) the tests that read real PDFs are
marked `@pytest.mark.samples` and skip with a reason; everything else runs. Expect
skips, not failures. Once `samples/` is in place they run. `tests/test_e2e.py`'s
sample tests additionally need Ollama with `llama3.1`, as above.

## Failure log

`failure_log.py` — `log_failure(document_id, predicted_type, correct_type, note)`
appends one JSON Lines record per misclassification to `failure_log.jsonl` at the
project root. Field names match `docs/2_ARCHITECTURE.md`'s `failure_log` SQLite
table, so this moves into SQLite later (unit #9) without a schema change.

**The record must stay de-identified.** Unlike `samples/`, `failure_log.jsonl` is
committed and shared — it travels. `document_id` is a filename or a hash, never a
path (a path leaks a client in the folder name even when the filename is clean).
`note` carries the classification decision only — never a name, an account number,
or a figure read out of the document. The full rule with worked examples is in
`failure_log.py`'s docstring; `tests/test_failure_log.py` asserts the record's exact
field set, so a new field fails that test before it can reach a shared file. Open
questions on the format are tracked in the issues, not here.

A reviewer's verdict reaches the log through `POST /review/correction`
(`review.record_correction()`): `document_id` is the SHA-256 `/ingest` returns —
never a filename, which is routinely the client's name — and the note is a reason
code from `review_policy.correction_reasons`, never free text. Confirmations are
logged as well as corrections, because thresholds are calibrated from both. The
Approve / Reject buttons on the page call it (see Reviewing a document, above),
with their choices read from `GET /review/options`. `tests/test_e2e.py` is the other
caller, comparing the classifier against hand labels on the public samples. `failure_log.jsonl` won't exist
until the first misclassification happens; that's expected, not a bug.

## What actually happens when you drop a PDF

`POST /ingest` runs, in order:

1. **`parser.py`** — `parse_pdf()`. Extracts text via `pypdf` with
   `extraction_mode="layout"` (fixes a real reading-order bug — see
   `docs/SESSION_NOTE_2026-08-22.md` bug #1). Returns filename, page count, char
   count, `has_selectable_text`, extracted text.
2. **`scope_gate.py`** — `check_scope()`. Deterministic title-pattern check against
   `knowledge_base.json`, first 500 chars only (not whole-document — see bug #2 in
   the same session note for why). In scope means a title pattern of any
   document type in `knowledge_base.json` matched; anything else gets
   `in_scope: false`.
3. **`classifier.py`** — `classify()`, only if in scope. Sends the text + every
   document type's `classifier_hints` from `knowledge_base.json` to a local Ollama
   `llama3.1` model, expects strict JSON back: `{doc_type, confidence,
   matched_signals}`.

Nothing is persisted (no DB, no filing yet). Every request is stateless — parse in,
JSON out.

## Dependencies

```
python -m pip install -r requirements.txt
```

| package | version | used by |
|---|---|---|
| `fastapi` | 0.128.0 | `app.py` |
| `uvicorn` | 0.39.0 | running the app |
| `pypdf` | 6.15.0 | `parser.py` |
| `python-multipart` | 0.0.22 | `app.py` — FastAPI cannot declare the upload endpoint without it |
| `requests` | 2.32.4 | `classifier.py` (talks to Ollama's HTTP API) |
| `cryptography` | 50.0.2 | `pypdf`, to open encrypted PDFs, including owner-locked ones anyone can read |

**Python 3.10 or newer.** `failure_log.py` annotates a parameter `str | None`,
which is a `TypeError` at import time on 3.9 — the failure is an import error
with no obvious link to the Python version, so it's worth stating here.

Test-only dependencies (`pytest`, and `httpx` for FastAPI's `TestClient`) are
deliberately not in `requirements.txt` — the app doesn't run them. They live in
`requirements-dev.txt`, which CI installs.

Plus a running Ollama instance with `llama3.1` pulled (see above).

## Project layout

```
app.py                  FastAPI app — POST /ingest, POST /review/correction, GET /review/options
parser.py               PDF -> text + metadata (pypdf, layout mode)
scope_gate.py           deterministic in-scope check, every type in knowledge_base.json
classifier.py           LLM classification via local Ollama, grounded in knowledge_base.json
static/index.html       drop-zone UI served at /
knowledge_base.json     source of truth for document types, hints, flags (v0.3) — never
                        hardcode doc rules in Python, see CLAUDE.md rule #1
harness.py              older batch/keyword-matcher prototype — separate track, see below
harness_demo_fixture.json  synthetic fixture harness.py currently runs against
samples/                10 real, verified-native-text sample PDFs (SOA/ROA/FSG/PDS)
docs/                   spec, architecture, session notes, to-do list — see below
```

## Two build tracks (still unmerged)

- **Live app track** (`app.py` / `parser.py` / `scope_gate.py` / `classifier.py`) —
  the one you run with the uvicorn command above. Parser → scope gate → LLM
  classifier are wired. Filing and the 11-rule flagging engine (`edge_case_flags` in
  `knowledge_base.json`) are **not** wired yet.
- **Harness/validation track** (`harness.py`) — batch keyword-matcher, currently runs
  against `harness_demo_fixture.json` (synthetic text), not the real `samples/` PDFs.
  Has two known unfixed bugs (KB-array-order tie-breaking, string-sorted date
  grouping) — see `docs/TO_DO_LIST.md` item 2.

Not yet decided whether `harness.py` becomes the offline batch tester alongside the
live app, or gets replaced by it. 

## Status / what's not built yet

- No filing — proposed filenames and event folders exist in `filing.py`, but
  `/ingest` does not return a full proposed path yet, and nothing is ever moved or
  renamed.
- Flags: the single-document rules (ROA situation, bundle) run on every upload;
  the rules that need other documents on file wait on persistence.
- Approve / Reject records a verdict on the type. Not yet: correcting the client,
  date or filename; roles (who may approve); hard stops greying out Approve.

## Contributing

**Read `CLAUDE.md` first.** It's not optional decoration — it's the ground rules
(knowledge base is the source of truth, nothing files silently, storage stays
abstracted) and the build sequence this project follows one step at a time. If a
change you're making conflicts with something in there, that's a conversation before
a PR, not after.

**Branches:**
- `main` is always runnable — `python -m uvicorn app:app` and `python -m pytest`
  both pass on it.
- Work in a branch per unit of work, not per session: `feature/<short-name>` for new
  capability (e.g. `feature/filing-engine`), `fix/<short-name>` for a bug, matching the build sequence you're picking up.
- One branch = one reviewable change. If you notice something unrelated while in
  there,  open a separate branch for it later — don't fold it into the current PR (see Commit Hygiene in `CLAUDE.md`).
- Open a PR into `main` when the unit is done and tests pass locally. Small, frequent
  PRs over one large one — same logic as the commit hygiene rule.

**Before opening a PR:**
- `python -m pytest` runs with no failures. On a bare clone the sample-backed tests
  skip with a reason — put `samples/` and `docs/sample_documents.labelling.md` in
  place (see below) to run them; they're not in git. `tests/test_e2e.py`'s sample
  tests also need Ollama running locally with `llama3.1` pulled — see Run it, above.
- CI (`.github/workflows/tests.yml`) runs the same `python -m pytest` on Python 3.10
  and 3.12 for every PR and every push to `main`, from a fresh install of
  `requirements-dev.txt`. It has no `samples/`, so the sample-backed tests skip
  there — that is expected. Nothing in CI calls Ollama.
- If your change touches document classification rules, the rule lives in
  `knowledge_base.json`, not hardcoded in Python (ground rule #1).
- If you hit a misclassification while testing, it's logged to `failure_log.jsonl`
  (tracked in git — don't gitignore it locally). It's the shared record both of us
  improve the classifier against.
- Update `CHANGELOG.md` with what you finished, and `docs/TO_DO_LIST.md` if you
  closed or opened an item.

**Client documents never enter git.** `.gitignore` blocks `*.pdf`, `*.docx`, `*.doc`
and `*.zip` by extension anywhere in the tree — a path rule like `samples/` misses a
PDF dropped at the repo root. It is **not retroactive**: it stops the next commit, it
does not scrub history. If a client document is already committed, raise it before
pushing on top of it.

**`docs/` and `samples/` — shared outside git:**
Both are gitignored — planning docs and sample advice documents aren't cleared for
a public repo, and `samples/` doesn't need to grow the repo's size. Get the current
copies from me directly (drive link / direct transfer, not a PR) and drop them in
at the same paths — `docs/` and `samples/` — so the code and docs above still find
them. If you have your own reference/sample documents to add for your own use,
follow the existing `TYPE_Description.pdf` naming (e.g. `FSG_YourProvider.pdf`) and
add a matching entry in `docs/sample_documents.labelling.md` with the expected
classification, then send me the updated folder the same way — not as a PR, since
neither path is tracked.

## Docs map
These are the documents handed off from me with the collaborator, as project's scaffold and used as reference while project is being built.

| file | what's in it |
|---|---|
| `docs/SYSTEM.md` | the spec — build from this |
| `docs/SYSTEM_v2.md` | a second spec draft, not yet reconciled with v1 (open item) |
| `docs/1_PRD.md`, `2_ARCHITECTURE.md`, `3_BUSINESS_CASE.md` | planning docs |
| `docs/ARCHITECTURE_TRACE.md` | what maps to what across the docs |
| `docs/HANDOVER.md` | sample sourcing decisions, judgment calls, source URLs |
| `docs/sample_documents.labelling.md` | hand-labelled expected results for `samples/` |
