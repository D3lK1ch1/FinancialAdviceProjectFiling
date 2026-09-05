# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 05-09-2026

### Done
- `requirements.txt` — the four runtime dependencies (`fastapi`, `uvicorn`,
  `pypdf`, `requests`) pinned to exact versions, with the Python 3.10 floor
  stated (`failure_log.py`'s `str | None` is an import-time `TypeError` on
  3.9). README's Dependencies section now installs from it instead of listing
  whatever happened to be in the environment.
- `.gitignore` — client documents blocked by extension (`*.pdf`, `*.docx`,
  `*.doc`, `*.zip`) anywhere in the tree, alongside the existing `docs`/
  `samples` path rules, which miss a PDF dropped at the repo root. Not
  retroactive; that limit is now written down in README's Contributing.
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
