# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 17-09-2026 — bundle detection

### Done
- `flags.py` — `multi_doc_bundle` now fires. #19's checkboxes 2 and 3: detect
  from the knowledge base, flag before splitting. `/ingest` passes per-page
  text (from #21) to the flag engine, which is why that had to land first —
  joined text cannot show where one document ends and the next begins.
- **Two signals, and the strong one needs no notion of type.** A page-number
  marker reading "page 1 of N" on any page but the first is direct evidence of
  a boundary. The example SOA inside ASIC's RG 90 file restarts at "Page 1 of
  23" on page 31 of 53, and that is what finds it.
- **The type signal is a TRANSITION, not a presence.** Every page of a real
  SOA carries its own title in a running header, so a second type's name
  appearing somewhere means nothing; the change from one type to another is
  the signal.
- **Nothing is ever split.** Candidate boundaries and proposed page ranges go
  to a human. A missed bundle is a flag nobody actioned; a wrong split cuts a
  record in half and nothing downstream can tell it happened.
- **`review_policy.open_question` is resolved, by a real case.** It asked
  whether medium severity should force review, given `roa_basis_unconfirmed`
  fires on every ROA. The answer is a per-rule override rather than a
  severity-wide rule: `multi_doc_bundle` sets `forces_review: true` because
  filing a two-document bundle as one document destroys a record rather than
  mislabelling one, and cannot be corrected later from what was filed.
  `roa_basis_unconfirmed` stays non-blocking, so the queue does not fill with
  every ROA.

### Two wrong turns, both caught by real documents
- **Frequency-based header suppression was wrong.** Ignoring types that appear
  on most pages looks sensible and hides exactly the boundary being looked
  for: in a real bundle the larger document's own running header legitimately
  appears on most pages of the whole file. Stapling a real FSG to a real ROA
  showed it — `roa` covered 9 of 11 pages and the boundary at page 3
  disappeared.
- **The excursion rule needed both halves.** `unisuper-flexi-pension-pds.pdf`
  reads `pds -> risk_profile -> pds`, because a PDS describes the risk profile
  of its investment options. Suppressing only the departure left the RETURN
  reported as the start of a new document.

### Validated against every real document available
- 25 files, no mismatches. Five are genuine bundles, twenty are not.
- **Three findings that correct earlier claims, all raised separately:**
  - `asic-cp284-example-soa-attachment.pdf` (p56) and
    `asic-rg90-example-soa-2013.pdf` (p40) **do** carry an appended Authority
    to Proceed. An earlier note on #19 said no real SOA+ATP case existed in
    the set — wrong; it was in different files from the one named for it.
  - `Example SOA.pdf` in the working copy is byte-identical to
    `samples/soa_atp/asic-rg90-example-soa-with-atp.pdf`.
  - **`PDS.pdf` is a bundle nobody had noticed** — an AustralianSuper PDS
    (pp1-18) with five appended forms: Join, Pay my super into, Combine your
    super twice, and a binding death benefit nomination. Native text, not
    scanned. See #23.

### Not done here
- #19's checkbox 4 (propose a split for approval as an action) and checkbox 5
  (`atp_without_advice_record` must not fire on an unsplit bundle) are
  separate. The second is stateful and waits on #8.
- The title signal's known weakness is recorded in the knowledge base rather
  than left to be discovered: a heading naming another type that never returns
  to the parent still reads as a boundary. Candidates are evidence for a
  human, so a wrong one costs a look rather than a record.

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

## Session 17-09-2026 — the review threshold

### Done
- `review.py` — `needs_review` with a reason, per #4's fourth checkbox.
  `/ingest` now returns a `review` block on every document: whether it can
  stand on its own, what threshold it was held to, and if it cannot, why not.
- `knowledge_base.json` — `review_policy`. A threshold per document type with
  the reasoning written next to it, a `default_threshold` for any type without
  its own entry, and the five reason codes a reviewer can be shown.
- **The only thresholds in the system were two numbers in a browser file.**
  `static/index.html` had `confidence >= 0.75` and `>= 0.5` and nothing else
  did — so the rule deciding whether a person looks at a client's advice
  record was a presentational detail of one page, applied to every document
  type equally, with no reasoning attached and invisible to the API. Moved to
  the knowledge base (ground rule #1); the page now colours the bar against
  the threshold the server sends and no longer decides anything.
- **Per type, because the cost of being wrong is not uniform.** Misfiling a
  PDS moves a product brochure. Misfiling an SOA builds an advice event around
  the wrong document. Advice records (`soa`, `roa`) sit at 0.80, the ATP and
  FDS at 0.75, inputs at 0.70, and the FSG and PDS at 0.60 — licensee- and
  issuer-wide documents that are not client-specific and are highly
  standardised in their titling. There is a test asserting advice records are
  held to the highest bar in the set, so the domain claim is pinned rather
  than implied.
- **Out of scope is a review reason, not a dead end.** It used to leave the
  pipeline with no type, no confidence and no flag — indistinguishable from an
  unreadable file. `unknown_type` is kept distinct from it: out of scope means
  nothing looked like ours, unknown type means the title gate matched and the
  classifier still could not name it.
- **A low-confidence document keeps its working.** It is not discarded and not
  blanked: the proposed type, the confidence and the matched signals all still
  come back, because a reviewer confirming a correct low-confidence answer is
  exactly the failure-log evidence ground rule #6 wants.
- `classifier_unavailable` is its own reason. An unreachable classifier is a
  property of the runtime, and must never be recorded against the document as
  a classification failure it did not cause.
- Reasons accumulate rather than short-circuit — two things wrong with a
  document is two things a reviewer should see.

### Open question, recorded rather than settled
- **Only high severity forces review.** Medium deliberately does not, because
  `roa_basis_unconfirmed` fires on every ROA and a queue that asks about every
  document gets ignored — the failure mode named in #20's direction note. But
  `multi_doc_bundle` is also medium, and filing a two-document bundle as one
  document is not something to wave through. That probably wants a per-rule
  `forces_review` override rather than a severity-wide rule. Left as
  `review_policy.open_question` because no real case has forced it yet.

### Not done here
- **The numbers are a judgement, not a measurement**, and `calibration_status`
  in the knowledge base says so in as many words. Nothing has been scored
  against a labelled sample set, because the classifier is not wired to one.
  They are set by the cost of being wrong per type, which is knowable now,
  rather than by observed accuracy, which is not. They should move once the
  failure log has entries.
- Nothing routes anywhere yet. `_Needs review` is returned as a proposed
  destination; filing itself is #10.

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
