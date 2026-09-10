# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 10-09-2026 — filing settings

### Done
- `knowledge_base.json` — `filing_model.stage_filing_overrides`. A firm can tailor
  how documents are grouped *inside* an advice event, without changing the two
  base axes. Stage 5 (implementation) is specified: `flat` (default),
  `by_provider`, `by_doc_type`. Firms differ most here — some want a folder per
  product issuer, some per document type, some neither.
- The base axes stay fixed. `client -> advice_event` is what
  `accuracy_mechanism` rests on: two axes that must agree is where the placement
  accuracy comes from. These settings subdivide within an event; they never
  become a third axis, because a sub-level cross-checks nothing.
- `by_provider`'s key is the **receiving** issuer — the entity the form
  instructs — not simply the first firm named. An application involving a
  rollover also names the funds being transferred out of, often prominently, and
  a balance question can name several more. Picking the first firm on the page
  would file a transfer under the fund the client is leaving.
- A rollover form is evidence about two providers. It files **once**, under the
  receiving issuer, and is **referenced** from the outgoing one rather than
  copied — the rule `shared_document_rule` already applies across advice events,
  applied here across providers. Never duplicate a signed form: two copies
  leaves it ambiguous which one is the record.
- `unresolved_key_rule` — no readable grouping key means file at event level and
  flag, never a guessed folder name. Same rule the model already applies to
  dates (`no_date`, never a filename guess). A folder named for the wrong issuer
  is worse than no folder, because it looks deliberate.
- Follows the precedent already set by `shared_document_rule`
  (`"configurable": true`, "Firms differ") and by `build_note`, which puts the
  folder scheme over results already produced so it can change without touching
  the classifier.

### Not done here
- **Nothing reads this yet.** Filing is not built — `/ingest` returns a
  classification and stops — so there is no proposed path for the setting to
  change. This is correct data now that takes effect when filing lands, the same
  shape as the ATP hints in #24.
- **The independence test is deferred, not skipped.** #26 asks that switching
  this setting leave `doc_type`, confidence and flags byte-identical, matching
  the three tests in #11. It cannot be written until there is a proposed path to
  hold constant, so it belongs with the filing work in #10 rather than here.
- Only stage 5 is specified. Other stages are deliberately absent until a firm
  asks for one.

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
