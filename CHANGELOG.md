# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 17-09-2026 — recording corrections other than the document type

### Decided (issue #12)
- **A generic `corrections` list, not a second pair of fields.**
  `predicted_type`/`correct_type` record one kind of correction: the tool said
  PDS, it was a file note. Reviewers make others — which of the three ROA
  situations a record sits on, and the confidence the system acted on versus
  what a person judged. A field pair per kind means a schema change for every
  future flag, so corrections are `{kind, predicted, correct}` entries in a
  list instead.

### Done
- `failure_log.py` — `log_failure()` takes an optional `corrections` list.
  Always written, empty when the document type was the only thing corrected,
  so no reader branches on whether the key exists.
- **The de-identification rule is expressed as a shape, not a warning.**
  `corrections` is the extension point every future flag will use, which makes
  it precisely where a client name would eventually be written by somebody
  being helpful at the end of the day. So: `kind` must be one of a known set,
  the only other fields are `predicted` and `correct`, **and there is no
  free-text field at all**. An unknown kind or an extra field raises and
  nothing is written.
- Three kinds to start: `doc_type`, `roa_situation`, `confidence`. Adding one
  is a deliberate act with a test behind it, not something a caller can
  invent — a log that silently accepts anything stops being evidence of
  anything.
- `tests/test_failure_log.py` — the exact-field-set guard now applies one
  level down, to each correction record, for the same reason it applies to the
  entry.

### Why this was blocking two things
- #12's ROA basis flag had nowhere to record a corrected situation.
- #37 keeps `confidence_raw` specifically so model drift is visible, and that
  comparison needs somewhere to live.

### Not done here
- **Nothing writes a correction yet**, because no approve/edit/reject action
  exists — that is #4's fifth checkbox and build step 5. This is the slot,
  ready for it.

## Session 17-09-2026 — three ROA situations, not four

### Decided (issue #33)
- **An ROA is permitted in THREE situations, not four.** The old list carried
  "hold / no-action (s946B(7))" and "no buy/sell (reg 7.7.10AAA)" as separate
  legislative bases. They are one situation: the Act's s946B(7) *is* the
  no-buy/sell provision, and reg 7.7.10AAA substitutes a notional version of
  it and sets its content requirements — the regulation's own title is "Record
  of advice without a recommendation to purchase or sell". ASIC's FAQ lists
  three. The old list counted one situation twice.
- **"Hold" is not a basis at all — it is what the advice recommends.** Which
  situation permits the ROA and what the advice says are two different things,
  and collapsing them is what made the old list wrong. An ROA can be *further
  advice* whose *recommendation* is no change, which is exactly what INFO 266
  attachment 2 is. The old four-entry list could not express that sentence.
- **Situation 2 carries a limb that is easy to miss:** no remuneration or
  benefit received, and conflicts disclosed. For a client on an ongoing fee
  arrangement that usually fails, which is why an annual-review "no change"
  recommendation is normally documented as further advice. Content alone never
  establishes that basis, and the knowledge base now says so.

### Changed
- `knowledge_base.json` — `legislation.four_kinds` becomes
  `legislation.situations`, three entries. `hold_no_action` is absorbed into
  `no_buy_sell`, which keeps the "take no action" phrasing as INFERRED signals
  while recording that content alone cannot establish the situation.
- `CLAUDE.md` — the domain-facts entry rewritten, including the correction
  that an earlier version said attachment 2 was "not further advice". It cites
  the further-advice situation, as do attachments 1 and 3.
- `flags.py`, `tests/test_flags.py` — three situations throughout.

### Recorded, not resolved
- **ASIC's 2021 media release describes INFO 266 as explaining "four
  exemptions".** Only three ROA situations have been found. The fourth may be
  a different exemption entirely rather than a fourth ROA basis. Kept in the
  knowledge base as `unresolved` so nobody re-derives the question from
  scratch — it does not change the three.

### What the sample set actually covers
- One situation, three times. All three INFO 266 attachments cite notional
  s946B(2) and reg 7.7.10AE. `example_status` on the other two situations says
  plainly that no real document of that kind exists to test against.

## Session 17-09-2026 — the ROA basis flag

### Done
- `flags.py` — the first flagging rule, and the seam the rest land in.
  `evaluate_flags(doc_type, text)` reads `edge_case_flags` from the knowledge
  base and returns the flags a document earns from its own contents. Wired
  into `/ingest`, which now always returns a `flags` list, and rendered in the
  result card so a flag that fires is a flag a person sees.
- `knowledge_base.json` — `roa_basis_unconfirmed`, medium severity. An ROA has
  four legislative bases — further advice (reg 7.7.10AE), hold/no-action
  (s946B(7)), small investment (s946AA), no buy/sell (reg 7.7.10AAA) — and
  which one applies decides what the record must contain and whether a prior
  SOA is required at all. Classifying a document as an ROA does not record
  that, so the question has to be asked.
- **It fires on every ROA, and it is the only rule in the set that works that
  way.** The others fire on an anomaly. This one fires on a property of the
  type, which is what `advice_classification_reference.md` §6 already says
  against the ROA row: "Medium: confirm which of 4 bases".
- **It proposes rather than asks blankly.** Where the text supports exactly one
  basis the flag names it and cites the phrases it matched, so a reviewer
  confirms or corrects one thing. Where it supports several, or none, it says
  so and proposes nothing — `determination` is `proposed`, `ambiguous` or
  `absent`, so the queue stays sortable.
- **Signals are split into `declared` and `inferred`,** and a declared basis
  wins. A document naming the situation it was written under outranks a basis
  read off the shape of the recommendation.

### Calibrated against a real document, not invented
- Run against ASIC INFO 266 attachment 1 (further advice), the first version
  returned **ambiguous** — the most canonical further-advice example in the
  public set, unreadable. Two real causes, both now fixed in the knowledge
  base and pinned by tests:
  - *"you will retain your existing policy features and benefits"* describes a
    **consequence** of advice, not a recommendation to hold. Retain- and
    continue-to-hold phrasing is gone from `hold_no_action` entirely; it is
    compatible with further advice that changes something else.
  - That ROA's own words include *"My advice is to make no changes to your XYZ
    Superannuation Fund"* while it increases the client's insurance cover. **No
    change to one holding, inside advice that changes another, is not a
    s946B(7) no-action ROA** — that basis needs the advice overall to be to
    take no action. Phrase matching cannot tell those apart, which is why the
    declared/inferred split exists and why this flag proposes rather than
    decides.
- After the fix the same document reads `proposed: further_advice`.
- Every rule in `edge_case_flags` now declares `"evaluation": "stateless"` or
  `"stateful"`, and a test asserts the engine only ever runs rules the
  knowledge base calls stateless. It cannot report having checked something it
  had no evidence for.

### Not done here
- **The failure log has nowhere to put a corrected basis.** `log_failure()`
  records `predicted_type` / `correct_type` — document type, not basis — and
  `tests/test_failure_log.py` asserts the exact field set on purpose, so the
  schema cannot grow quietly. A reviewer correcting a basis is a real
  correction that ground rule #6 wants captured, and it needs a decision
  before any field is added. Raised on #12 rather than settled here.
- **The other ten rules are declared, not implemented.** Five are stateful and
  wait on persistence (#8). `multi_doc_bundle` is stateless and belongs to
  #19, which now has the page boundaries it needs.
- **No review threshold.** The flag says "review" and nothing routes on it yet
  — that is #4's own checkbox, and `_Needs review` filing is #10.
- **Nothing fires end to end without Ollama.** The rule keys on the classified
  type, deliberately, so that a document merely mentioning an ROA is not asked
  which legislative basis it is. With the classifier unreachable there is no
  type, so no flag. Verified with the classifier stubbed.

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
