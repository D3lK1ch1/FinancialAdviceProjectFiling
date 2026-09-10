# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

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
