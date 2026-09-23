# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 24-09-2026 — date extraction, and closing GH#9 honestly

### Done
- `dates.py` / `tests/test_dates.py` (23 tests) — date extraction (GH#8 box 2 / unit 5).
  Four units: `find_date_candidates` (date-shaped substrings + page + context, no
  validity judgement yet), `parse_day_first` (explicit day-first — `03/04/2025` → 3
  April — rejects invalid dates and 2-digit years rather than reordering or guessing),
  `select_date` (`declared`/`inferred`/`ambiguous`/`absent`, mirroring #32's ROA-basis
  flag *engine shape* only — checked against a live review comment on #32 first, which
  confirms the engine itself is unaffected by that PR's disputed legislative content),
  `extract_dates(parsed)` (integration against `parser.py`'s real return shape).
- **Empirically checked before designing `select_date`, not assumed:** ran the real
  `samples/*.pdf` text through candidate-matching first. Bare `Month YYYY` dates
  ("Issued: November 2021 Updated: November 2024", repeated per-page ASIC footers) are
  template publication stamps, never the client's advice date — confirms Unit 1's regex
  was already right to exclude them.
- **A real bug found by the real-sample spot-check, not by unit tests:** two mentions of
  the identical date in different sentences were miscounted as competing candidates,
  returning `ambiguous` on 2 of 3 single-date FSGs (`FSG_AustralianSuper`, `FSG_UniSuper`).
  Fixed by grouping non-boilerplate candidates by resolved date value instead of raw
  candidate count. Pinned by
  `test_same_date_confirmed_by_multiple_mentions_is_not_ambiguous`. Final read across all
  10 real samples: 3 `declared`, 3 `inferred`, 4 genuinely `ambiguous` (two documents have
  no declared date label at all, two have multiple real competing dates in the text).
- **GH#9's two undone boxes are now actually true**, without touching the closed issue
  (still closed, boxes still ticked — the record is honest because the work exists, not
  because the record was edited). `llm` marker + default deselect: `pytest.ini` sets
  `addopts = -m "not llm"`, `test_ingest_full_pipeline_in_scope` (the one test that hits
  live Ollama) carries the marker. Verified: default run shows `4 deselected`, `pytest -m
  llm` overrides it and still fails loudly on an unreachable model. Side effect: bare
  `pytest` is now safe to run on this machine despite the `qwen2.5:3b`/`llama3.1`
  mismatch — the suite as a whole no longer needs 0.3 done first, only `pytest -m llm`
  does. File-hygiene CI job: new `file-hygiene` job in `.github/workflows/tests.yml`,
  `pull_request`-only, diffs base→head for added `*.pdf`/`*.docx`/`*.doc`/`*.zip`, fails
  with an explicit error. Verified both directions in a throwaway repo before trusting it.
  Points at README.md's "Client documents never enter git" — the original issue text said
  "Contributing", but no `CONTRIBUTING.md` exists in this repo.

### Not done here
- Date extraction is not wired into `/ingest` — `extract_dates()` exists standalone,
  nothing calls it from the live app yet.
- The KB's existing `no_date` edge-case-flag rule is not fired by this work — the output
  is shaped for a future flag-engine unit to consume, not wired to it.
- `docs/sample_documents.labelling.md` still has zero hand-labelled expected dates for
  the real samples. The real-PDF check this session stayed eyeball-only by design;
  building actual ground truth is still a separate, undecided future task.

## Session 22-09-2026 — CI workflow, and the runtime dependency it found missing

### Done
- `.github/workflows/tests.yml` — runs `python -m pytest -rs` on every PR and every
  push to `main`, on Python 3.10 (the documented floor) and 3.12, from a fresh
  install. `-rs` prints the skip reasons in the log, so a skipped test is never
  silent. No Ollama, no `samples/`: it runs the no-documents tier only.
- `requirements-dev.txt` — `requirements.txt` plus `pytest` and `httpx`, pinned.
  The README already said test-only dependencies belonged with CI; this is where.
- **`requirements.txt` was missing `python-multipart`.** FastAPI cannot declare an
  `UploadFile` endpoint without it, so in a fresh environment `import app` raised
  `Form data requires "python-multipart"` — and so did the README's own
  `pip install -r requirements.txt` followed by `uvicorn app:app`. It never showed
  because every machine that had run the project already had the package. Found by
  installing into an empty virtualenv, which is what CI does on every run.
  Pinned at `0.0.22`, the version already working alongside `fastapi==0.128.0`.
- README: the install step before `pytest`, the new dependency row, and what CI does.

### Not done here
- **The workflow has not run on GitHub.** Its YAML parses and its steps were run by
  hand in fresh virtualenvs on 3.11 and 3.12 (60 passed, 7 skipped on both), but a
  workflow is only really tested by running. Python 3.10 could not be tried locally
  (the launcher's 3.10 entry points at a folder that no longer exists), so 3.10's
  first real run is CI's.
- **The file-hygiene check** (#9, fourth checkbox): fail any PR that adds a
  `*.pdf`/`*.docx`/`*.doc`/`*.zip`.
- **`main` is not protected**, so CI reports but blocks nothing.

## Session 21-09-2026 — CI test tiers

### Done
- **A bare clone no longer fails.** Baseline on `origin/main` with no `samples/`:
  5 failed, 60 passed, 2 skipped. The five were the four `test_e2e.py` sample
  tests and `test_fsg_is_not_misread_as_soa`, all `FileNotFoundError` — a missing
  input reading as a broken change. Now: 0 failed, 60 passed, 7 skipped.
- `@pytest.mark.samples` marks the 25 tests that read real PDFs; `conftest.py`
  skips them with a reason when `samples/` has no PDFs, and says where to get
  them. `pytest.ini` registers the marker.
- The two old skips said only `got empty parameter set` — true, and no help to
  anyone. The skip mark is added ahead of pytest's own so the useful reason wins.
- With `samples/` present nothing changes: 80 passed excluding `test_e2e.py`.

### Not done here
- **`llm` marker and default deselect** (#9, second checkbox). `test_e2e.py`'s
  docstring chooses to fail loudly rather than skip when Ollama is missing, and
  that choice is being reversed in part — it needs its own decision, so it is its
  own unit.
- The **file-hygiene check** (fourth checkbox). CI itself is the entry above.
- A `samples/` folder with only *some* of the files still fails on the missing
  one. That is left loud on purpose: an incomplete folder is a real problem.
- `test_e2e.py`'s four sample tests were not run with `samples/` present — they
  need `llama3.1`, and this machine's Ollama has `qwen2.5:3b`.

## Session 10-09-2026 — file notes

### Done
- `knowledge_base.json` — added the `file_note` document type. Stage 3 (advice
  construction) now lists it. Data only; no Python changed.
- **Why it is the biggest gap in the type set.** Safe harbour steps 3-6 —
  assess competence, investigate, base the advice on that investigation,
  prioritise the client — are four of the seven, they happen before the advice
  record is written, and the file note is the only paper trail they leave.
  `advice_classification_reference.md` §2 maps that stage to "(internal file
  notes)". Stage 3 previously pointed at `soa`, which is stage 4's document.
- **The failure was confident, not uncertain.** With no `file_note` type the
  only patterns that could match were the ones the note cites, so a meeting note
  came back `{'in_scope': True, 'likely_type': 'pds'}` — a Product Disclosure
  Statement, stated with confidence.
- **A file note often records a conversation with the PROVIDER, not the client**
  — calling a fund about a balance, a rollover or a policy. Titles carry the
  subject after a dash or "on" ("File Note - <fund>"), so a fund's name in one
  says who was contacted, not who issued it. That is now the first thing
  `distinguishing_signals` and `confusable_with` say.
- `advice_record_role` is `false`. A file note describes advice being prepared;
  it is never the advice record.
- `tests/test_scope_gate.py` — seven cases, all plain text, no `samples/`
  needed: four file-note shapes including the dash-subject and ALL-CAPS forms,
  a provider-named note, and two regression cases proving a genuine SOA and PDS
  still win their own titles.

### Not done here
- **`.docx` still returns HTTP 500.** File notes are typically Word documents,
  and `app.py` calls `parse_pdf()` on whatever is uploaded with no format check.
  So this classifies correctly through the scope gate but cannot yet run
  end-to-end on the format it usually arrives in. Depends on #5.

## Session 10-09-2026 — knowledge base

### Done
- `knowledge_base.json` — `advice_process_stages` stage 6 no longer names two
  document ids that `documents` does not define. `ongoing_fee_consent` was an id
  mismatch: the type exists as `fee_disclosure_statement`, whose own `name` reads
  "Fee Disclosure Statement / Ongoing Fee Consent", and it was already listed in
  the same stage — so the reference was a duplicate, not a missing type.
  `annual_review` is removed because it is not a document type at all: an annual
  review is a service event, and the documents it produces are the FDS and, where
  something changed, a new ROA. `advice_classification_reference.md` §2 says so
  directly ("Ongoing review ... FDS (+ new ROA)"), and §6's master mapping table
  carries no annual-review row.
- Stage-to-document mapping is what advice-event grouping (#10) will key on, so a
  stage naming a type that does not exist is a defect in that mapping rather than
  a cosmetic one.

### Not done here
- Stage 5 still names `application_forms`, which `documents` does not define. That
  one is a genuine gap rather than a bad reference: the reference doc's §6 table
  carries an "Application / insurance" row with legal basis **s1012**, so it is a
  legislated type and belongs in the knowledge base. Adding it is its own change
  (#23, checkbox 2). The self-consistency test (#23, checkbox 4) lands with it,
  because it cannot pass until then.

## Session 05-09-2026

### Done
- `requirements.txt` — the four runtime dependencies (`fastapi`, `uvicorn`,
  `pypdf`, `requests`) pinned to exact versions, with the Python 3.10 floor
  stated (`failure_log.py`'s `str | None` is an import-time `TypeError` on
  3.9). README's Dependencies section now installs from it instead of listing
  whatever happened to be in the environment.
- `failure_log.py` / `tests/test_failure_log.py` — the de-identification rule for
  `failure_log.jsonl` is now written down (it's committed and shared, so
  `document_id` is a filename or hash and never a path, and `note` carries the
  classification decision only), and a test asserts the record's exact field set
  so a new field can't be added without failing first (issue #3).
- `.gitignore` — client documents blocked by extension (`*.pdf`, `*.docx`,
  `*.doc`, `*.zip`) anywhere in the tree, alongside the existing `docs`/
  `samples` path rules, which miss a PDF dropped at the repo root. Not
  retroactive; that limit is now written down in README's Contributing.
- `app.py` / `classifier.py` / `scope_gate.py` — the supported document-type set
  now comes from `knowledge_base.json` instead of the same four-type tuple
  hardcoded in three files. Every KB type is in scope, and the classifier's
  hint block covers all of them (they already carry complete `classifier_hints`, so
  this is a data change, not new matching logic). Previously the unsupported
  types — most of a firm's real intake — left the pipeline as `in_scope: False`
  with no type and no flag, indistinguishable from an unreadable file (#12).
- `knowledge_base.json` — the `car` (Client Advice Record) document type is
  removed. DBFO Tranche 2 is not law, and the system does not classify or file
  document types that are not legislated. `reform_watch` keeps the record of the
  reform and now carries the decision. The transition seam is
  `advice_record_role`, still carried by `soa` and `roa`, so role-keyed logic
  stays exercised; and because the supported type set is read from the knowledge
  base rather than hardcoded, adding the successor on enactment is one entry and
  no Python. That property is now asserted by a test instead of assumed, which
  the placeholder entry never did (#12).
- `scope_gate.py` — candidate types now rank on earliest match position, not on
  summed pattern length. Length was standing in for confidence: "Product
  Disclosure Statement" (28 chars) outranked "Record of Advice" (16), so an ROA
  that cites the PDS of the product it discusses came back as a `pds`. A
  document's own title is at the top; a type it merely cites appears further
  down. Ties break on distinct patterns matched (#4).
- `scope_gate.py` — case sensitivity is now decided per pattern from the pattern's
  own shape: mixed-case titles match in any casing, all-caps acronyms stay
  case-sensitive. An ALL-CAPS cover page previously matched nothing and left the
  pipeline as `in_scope: False` with no flag. Casefolding the acronyms too would
  have traded that for `car`'s "CAR" matching the ordinary word "car" (#4).
- `scope_gate.py` — `title_patterns` now match on word boundaries instead of bare
  substrings. Six of them are three-letter acronyms, so `"ROA" in head` was also
  true for ROAD and BROADWAY, and a letterhead street address sits inside exactly
  the 500-char title window the gate reads. Out-of-scope documents were entering
  the pipeline as ROAs. Prerequisite for widening the supported type set (#12).

## Session 05-09-2026 — knowledge base

### Done
- `knowledge_base.json` — the Authority to Proceed's hints now key on what the
  document *does* rather than what it looks like. Firms name this one
  inconsistently (four title variants already), so title is weak evidence; the
  substance is constant: a named party, specific actions, and a client's grant of
  authority to act. Adds the first-person grant, the authorised party as a key
  field, and the distinction from application forms — both are signed lists of
  actions, but an ATP empowers the ADVISER while application forms instruct the
  PRODUCT ISSUER.

## Session 05-09-2026 — parser

### Done
- `parser.py` — `parse_pdf()` now returns per-page text alongside the joined text.
  Extraction was already page by page; the boundaries existed and were discarded
  on the join. They are the only evidence a bundle split point can be argued from
  (#19). `"\n".join(pages) == extracted_text` always holds, so the two views
  cannot disagree. `/ingest` does not echo `pages` — no consumer yet, and it would
  roughly double the payload.
- `tests/test_parser.py` — multi-page PDFs are now built in the test with `pypdf`
  itself, so the file runs on a bare clone. `test_parse_pdf_returns_expected_keys`
  previously indexed `samples/` and raised `IndexError` rather than guarding the
  record shape when the samples weren't present.

## Session 31-08-2026

### In progress
- Step 3 of the build sequence (`CLAUDE.md`): running real documents through the
  live-app track, fixing failures, calibrating classifier confidence.

### Not started
- Filing (proposed destination + rename) — `/ingest` returns a classification only,
  nothing is moved or renamed yet.
- Flagging engine — `knowledge_base.json`'s 11 `edge_case_flags` rules exist in the
  data but aren't read by any code yet.
- Approve/Edit/Reject UI — everything today is read-only output on the page.
- Reconciling `docs/SYSTEM.md` and `docs/SYSTEM_v2.md` into one spec.
- Deciding whether `harness.py` (harness/validation track) stays as an offline
  batch tester alongside the live app, or gets replaced by it.

## Done
### Live app track
- `parser.py` — PDF text extraction via `pypdf`, layout mode.
- `scope_gate.py` — deterministic in-scope check (SOA/ROA/FSG/PDS) against
  `knowledge_base.json`.
- `classifier.py` — LLM classification via local Ollama (`llama3.1`), grounded in
  `knowledge_base.json`'s `classifier_hints`.
- `app.py` — `POST /ingest` wiring parser → scope gate → classifier, plus a
  drop-zone UI at `/`.
- `failure_log.py` — JSON Lines misclassification log, schema matches the future
  SQLite `failure_log` table in `docs/2_ARCHITECTURE.md`.
- Test suite: 40 tests across parser, scope gate, classifier, e2e, and failure log
  (`tests/`).

### Harness/validation track
- `knowledge_base.json` (v0.3) — document types, classifier hints, stages, flags.
- `harness.py` — keyword-matcher prototype, runs against
  `harness_demo_fixture.json` (synthetic text, not real samples yet)
