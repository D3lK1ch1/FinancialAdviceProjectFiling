# Advice Document Classifier & Filing System

Source of truth for **how to run this project**. For what it does and why, see
`CLAUDE.md` (ground rules) and `docs/SYSTEM.md` (spec). For what's already been done, see `CHANGELOG.md`

> **`docs/` and `samples/` are not in this git repo.** They're gitignored on purpose since planning docs and sample documents are client/collaborator-sourced material, not cleared for public repo (in discussion). A fresh clone will build and pass most tests but won't have them.

## Run it

```
python -m uvicorn app:app --port 8000
```

Then open `http://127.0.0.1:8000/` — drop a PDF on the page.

**Also needs, for classification to actually run (not just parsing/scope-check):**
- [Ollama](https://ollama.com) running locally on the default port (`localhost:11434`)
- the `llama3.1` model pulled: `ollama pull llama3.1`
- Once pulled, will stay in default port and run alongside project

If Ollama isn't running, `/ingest` still works — you just get a `classifier_error`
in the response instead of a `doc_type`.

Ollama is used for the purposes of this project, but API keys from LLMs such as Anhropic (Claude) and OpenAI (Codex) can be considered and built upon.

## Run the tests

```
python -m pytest
```

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
| `tests/test_failure_log.py` | `log_failure()` appends correctly-shaped JSON Lines records; handles `None` predicted type; appends without overwriting |

40 tests total. More test files land as the suite grows — see `docs/TO_DO_LIST.md`
for what's still open.

## Failure log

`failure_log.py` — `log_failure(document_id, predicted_type, correct_type, note)`
appends one JSON Lines record per misclassification to `failure_log.jsonl` at the
project root. Field names match `docs/2_ARCHITECTURE.md`'s `failure_log` SQLite
table, so this moves into SQLite later (unit #9) without a schema change.

No review UI exists yet to capture human corrections, so the current caller is
`tests/test_e2e.py` — it already has both a real classifier prediction and a
hand-labelled correct answer for every sample. `failure_log.jsonl` won't exist
until the first misclassification happens; that's expected, not a bug.

## What actually happens when you drop a PDF

`POST /ingest` runs, in order:

1. **`parser.py`** — `parse_pdf()`. Extracts text via `pypdf` with
   `extraction_mode="layout"` (fixes a real reading-order bug — see
   `docs/SESSION_NOTE_2026-08-22.md` bug #1). Returns filename, page count, char
   count, `has_selectable_text`, extracted text.
2. **`scope_gate.py`** — `check_scope()`. Deterministic title-pattern check against
   `knowledge_base.json`, first 500 chars only (not whole-document — see bug #2 in
   the same session note for why). Only SOA/ROA/FSG/PDS are in scope; anything else
   gets `in_scope: false` and stops here.
3. **`classifier.py`** — `classify()`, only if in scope. Sends the text + the four
   document types' `classifier_hints` from `knowledge_base.json` to a local Ollama
   `llama3.1` model, expects strict JSON back: `{doc_type, confidence,
   matched_signals}`.

Nothing is persisted (no DB, no filing yet). Every request is stateless — parse in,
JSON out.

## Dependencies

```
python -m pip install -r requirements.txt
```

Pinned to exact versions, so a clone installs what this was built and tested
against rather than whatever is current that week:

| package | version | used by |
|---|---|---|
| `fastapi` | 0.128.0 | `app.py` |
| `uvicorn` | 0.39.0 | running the app |
| `pypdf` | 6.15.0 | `parser.py` |
| `requests` | 2.32.4 | `classifier.py` (talks to Ollama's HTTP API) |

**Python 3.10 or newer.** `failure_log.py` annotates a parameter `str | None`,
which is a `TypeError` at import time on 3.9 — the failure is an import error
with no obvious link to the Python version, so it's worth stating here.

Test-only dependencies (`pytest`, and `httpx` for FastAPI's `TestClient`) are
deliberately not in `requirements.txt` — they belong with contributor-runnable
tests and CI, which is its own open item.

Plus a running Ollama instance with `llama3.1` pulled (see above).

## Project layout

```
app.py                  FastAPI app — one endpoint, POST /ingest
parser.py               PDF -> text + metadata (pypdf, layout mode)
scope_gate.py           deterministic in-scope check (soa/roa/fsg/pds only)
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

- No filing (proposed destination + rename) — classification result is returned,
  nothing is moved or renamed.
- No flagging engine wired — `knowledge_base.json`'s 11 `edge_case_flags` rules are
  read nowhere in the code yet.
- No Approve/Edit/Reject UI — everything today is read-only output on the page.

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
- `python -m pytest` passes. Most of the suite needs your local `samples/` and
  `docs/sample_documents.labelling.md` in place first (see below) — they're not in
  git, so a bare clone won't have them. `tests/test_e2e.py` also needs Ollama
  running locally with `llama3.1` pulled — see Run it, above.
- If your change touches document classification rules, the rule lives in
  `knowledge_base.json`, not hardcoded in Python (ground rule #1).
- If you hit a misclassification while testing, it's logged to `failure_log.jsonl`
  (tracked in git — don't gitignore it locally). It's the shared record both of us
  improve the classifier against.
- Update `CHANGELOG.md` with what you finished, and `docs/TO_DO_LIST.md` if you
  closed or opened an item.

**Client documents never enter git.** `.gitignore` blocks `*.pdf`, `*.docx`,
`*.doc` and `*.zip` by extension, anywhere in the tree. That's on purpose:
the `docs`/`samples` path rules only cover the two folders anyone remembered
to list, and miss a client PDF dropped at the repo root while testing. **The
rule is not retroactive** — it stops the next commit, it does not scrub
anything already in history. If a client document has already been committed,
say so before you push anything on top of it: getting it out means rewriting
history, not a follow-up commit.

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
