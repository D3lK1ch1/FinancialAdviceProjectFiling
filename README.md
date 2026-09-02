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

No `requirements.txt` exists yet (known gap — not fixed by this README). What's
installed and in use, confirmed in this environment:

| package | used by |
|---|---|
| `fastapi` | `app.py` |
| `uvicorn` | running the app |
| `pypdf` | `parser.py` |
| `requests` | `classifier.py` (talks to Ollama's HTTP API) |

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

## Proposed improvements (nothing here is built)

Findings from a read-through of `app.py`, `scope_gate.py`, `classifier.py` and
`knowledge_base.json` at `2ed1a12`. This section is deliberately notes-only: each
item is written so it can be picked up later as its own `feature/` or `fix/`
branch per Contributing below, rather than folded in as an unreviewed change.
Every item is measured against a rule this project already set for itself —
`CLAUDE.md`'s ground rules, `docs/1_PRD.md`, or `docs/security-checklist.md` —
and cites which one.

### Security

None of these are defects in a Phase-1 POC that stays on localhost. They're the
gap between here and `docs/security-checklist.md`'s "required controls for a web
app", and the point is that **nothing in the code currently enforces the
localhost boundary** — the checklist says "do not expose the app to the public
internet before security review", but `uvicorn app:app --host 0.0.0.0` is one
flag away and there's no guard.

1. **`/ingest` is unauthenticated.** Any caller who can reach the port can upload
   a document and read back its text. Checklist calls for "authenticated access"
   and "role-based permissions".
   *Steps:* add a single shared-secret header check as a FastAPI dependency now
   (a stand-in, not the final auth); make it the one place a real identity
   provider is wired in later; add a test that an unauthenticated `POST /ingest`
   returns 401.

2. **Upload size is unbounded.** `await file.read()` in `app.py` reads the whole
   upload into memory before anything validates it. A single large file is enough
   to exhaust memory — no attacker sophistication required.
   *Steps:* read in chunks against a max-bytes ceiling, return 413 past it; put
   the ceiling in `knowledge_base.json` rather than in Python, per ground rule #1;
   test at the boundary and one byte over.

3. **No file-type validation before parsing.** `parse_pdf()` is handed whatever
   arrives. The checklist lists "file upload validation", "PDF/Word parsing
   safety", "no direct file execution from uploaded content" and "quarantined
   temp folder".
   *Steps:* check the `%PDF-` magic bytes (not the filename extension, which the
   caller controls) and reject anything else before `parse_pdf()` is reached;
   treat `file.filename` as untrusted — never join it into a path.

4. **The response echoes the full document text.** `/ingest` returns
   `extracted_text` in the JSON. With a real SOA that is a client's complete
   financial position travelling back over the wire and into any proxy or
   browser-devtools log along the way.
   *Steps:* drop `extracted_text` from the default response; keep it behind an
   explicit `?include_text=true` for local debugging; make sure exception
   handlers never put document text in a log line.

5. **Local-only classification is a feature — write it down.** `classifier.py`
   posting to `localhost:11434` means document text never leaves the machine.
   That's the right call for client files and it should be recorded as a decision
   so it isn't casually swapped for a hosted API. The README already notes that
   Anthropic/OpenAI keys "can be considered" — worth adding what that would
   require first: Australian data residency, a DPA, and a contractual no-training
   guarantee.

### File hygiene

1. **No `requirements.txt`.** Already flagged under Dependencies. It's a hygiene
   item because "review dependencies before installation" is the first line of
   `docs/security-checklist.md`, and there's currently no manifest to review.
   *Steps:* pin `fastapi`, `uvicorn`, `pypdf`, `requests` to exact versions; add
   the install line to Run it; note that Ollama stays a separate prerequisite.

2. **Keep client documents out of git history permanently.** `.gitignore` already
   excludes `docs` and `samples` for exactly this reason. The failure mode is a
   contributor adding an advice document at some *other* path — a repo-root
   `Example SOA.pdf`, a zip of a working folder — where the ignore rules don't
   reach. An SOA or ROA is a named client's financial position, and this repo is
   public.
   *Steps:* add `*.pdf`, `*.docx`, `*.zip` to `.gitignore` as a catch-all
   alongside the path rules; consider a pre-commit hook that refuses those
   extensions; and note in Contributing that a `.gitignore` fix does **not**
   remove anything already committed — that needs history rewriting and a
   credential/document review, so the cheap fix is never letting it land.

3. **`failure_log.jsonl` is tracked in git — keep it de-identified.** It's meant
   to be, and the shared improvement loop depends on it. But it records
   `document_id` and a free-text `note`, and it's the one client-adjacent file
   that is deliberately committed to a public repo.
   *Steps:* state in the Failure log section that `document_id` is a filename or
   hash and the note describes the *document type* decision, never a client name
   or a figure; add a test asserting the written record contains only the
   expected keys.

4. **Two unmerged build tracks is a hygiene cost, not just an open question.**
   `harness.py` and the live app both classify, from the same knowledge base, by
   different logic. Until one is retired, every rule change has two homes and the
   two known `harness.py` bugs stay ambiguous — bugs to fix, or dead code.
   *Steps:* make the call, record it in `CHANGELOG.md`, and either delete the
   loser or move it under `prototypes/` so no one reads it as live.

### Making it suitable for a real firm

1. **The scope gate is case-sensitive, so caps cover pages fall out silently.**
   `check_scope()` does `p in head`, and the `title_patterns` in
   `knowledge_base.json` are Title Case — `"Statement of Advice"`, `"Record of
   Advice"`. A cover page typeset as **"STATEMENT OF ADVICE"** — ordinary in
   advice documents — matches nothing, so `in_scope: false`, `classifier.py`
   never runs, and the document leaves the pipeline with no type, no confidence
   and no flag. It doesn't reach review, because being out of scope isn't
   modelled as something to review.
   *Steps:* casefold both sides of the comparison in `check_scope()`; add a test
   per doc type with an all-caps title; keep the patterns in
   `knowledge_base.json` untouched, per ground rule #1.

2. **Tie-breaking on matched-pattern length can pick the wrong type.**
   `sum(len(p) for p in matched)` rewards long pattern strings, not strong
   evidence. An SOA cover page that also names `"Product Disclosure Statement"`
   (28 chars) outscores its own `"Statement of Advice"` + `"SOA"` (22) and comes
   back as a PDS. The 500-char window reduces how often this happens; it doesn't
   remove it.
   *Steps:* score on earliest match position (a title sits above a
   cross-reference) or on number of distinct patterns matched; better, return the
   full candidate set and let the classifier resolve it — `docs/1_PRD.md` §2.2
   already asks for a candidate set rather than a silent single answer.

3. **Confidence is the model's own self-assessment.** `classify()` passes
   `parsed.get("confidence", 0.0)` straight through. `docs/2_ARCHITECTURE.md` §4
   requires confidence "calculated from multiple signal types, not only
   keywords", and `docs/1_PRD.md` §2.1 requires the evidence to be recorded. An
   LLM's stated confidence is neither calibrated nor evidence — and the prompt
   asks for `matched_signals` "actually present in the document text" without
   anything checking that they are. This matters more than the two bugs above,
   because ground rule #2 routes to review on low confidence: an uncalibrated
   number decides what a human ever sees.
   *Steps:* after parsing the response, verify each `matched_signals` phrase
   really occurs in `extracted_text` and drop the ones that don't; derive the
   confidence the system acts on from the verified-signal proportion plus
   agreement with the scope gate's `likely_type`; keep the raw model number as a
   separate field so the two can be compared in `failure_log.jsonl` over time.

4. **Nothing routes to review yet, because there's no threshold.** Ground rule #2
   is "never file silently; on low confidence route to `_Needs review` with a
   reason". Today `/ingest` returns whatever it got and stops, which is honest
   for Phase 1 — but the threshold is the piece that makes the rule real, and it
   should land with filing rather than after it.
   *Steps:* put the per-doc-type threshold in `knowledge_base.json`; return an
   explicit `needs_review` boolean and a reason code with every result; make
   out-of-scope a review reason rather than a dead end (see item 1).

5. **The failure log has no path for a human correction.** `log_failure()` takes a
   `correct_type`, but the only caller is `tests/test_e2e.py`, which knows the
   answer from a hand-label. In a firm the correct answer comes from a reviewer,
   and without that the improvement loop only ever learns from the sample set.
   *Steps:* when the Approve/Edit/Reject UI lands (build sequence step 5), have
   Edit and Reject write a `log_failure()` record with the reviewer's chosen type
   and reason code — that closes ground rule #6's loop with real firm data
   instead of test fixtures.

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
