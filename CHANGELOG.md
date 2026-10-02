# Changelog

What's actually done, in progress, and not started — so nobody re-does or overwrites
a finished step (see Contributing in `README.md`). Newest at top. 

## Session 02-10-2026 — review screen, unit B: Approve / Reject on the result card

### Done
- `static/index.html` — every result card ends in a verdict block. **Approve**
  records `confirmed` for the proposed type. **Reject** opens two dropdowns,
  *what it actually is* and *why*, with the chosen reason's meaning shown;
  Submit stays disabled until both are picked. A recorded verdict replaces the
  buttons with "Recorded … Nothing has been filed."; a refusal shows the
  server's own message. Build step 5, first half; GH#4 box 5, screen half.
- The choices come from `GET /review/options` (unit A), never from a list in
  the page. The reject list leaves out the type the tool proposed, because the
  server refuses a "correction" that changes nothing.
- Out-of-scope documents get Reject only (nothing to approve). The
  "classifier unavailable" card gets no buttons: a runtime failure is not a
  verdict on the document.
- Every button is disabled while a verdict is being sent, so a double click
  records once.
- `tests/test_review_buttons.py` — 16 tests on the server side of every click:
  Approve accepted for all 9 types, Reject accepted for all 5 reasons, a
  same-type "rejection" refused, and the page holding no copy of the type ids
  or reason codes.

### Checked by hand (engineer)
- End to end with Ollama running: Approve on `FSG_PeninsulaWealth.pdf` wrote one
  `reviewer:confirmed` line to `failure_log.jsonl`, keyed by the SHA-256 hash,
  no filename. The mechanics work.
- "Couldn't reach the classifier … WinError 10061" is Ollama's local server not
  running (port 11434 on this machine), not the network. Check
  `http://localhost:11434` reads "Ollama is running" before testing.

### Handed over, not done here
- **Which verdicts are right is a domain judgement**, so acceptance testing of
  what to approve or reject on the samples goes to the domain collaborator.
  The engineer checked that a click is recorded correctly; whether the click
  was the right one is hers to judge.
- Two findings from this session for that review: `FSG_UniSuper` scored 0.32
  because the model returned three `key_fields` labels as quotes ("services
  offered", "fees/commissions"), which the confidence check rightly marked
  down — a classifier prompt fix. `PDS_AustralianSuper` is held by the bundle
  hard stop because five blank application forms are appended (pp19–36): is a
  PDS with its own forms one document?
- No roles yet: anyone can approve. `approval_policy` (#54) needs a login
  first. Hard stops greying out Approve are unit C.

## Session 02-10-2026 — review screen, unit A: the choices it offers

### Done
- `GET /review/options` — the document types and reason codes the Approve/Reject
  screen offers, read from `knowledge_base.json` so the page keeps no copy of
  them (ground rule #1). Approve sends `confirmed`; a reject picks one of the
  other five codes. No free-text "why".
- `tests/test_review_options.py` — 5 tests, each checked against the knowledge
  base, including that every choice offered is one `/review/correction` accepts.
- **`app.py` now opens the knowledge base as UTF-8.** On Windows it defaulted to
  cp1252 and garbled every em dash on the way to the screen ("—" became "â€”").
  Found by the new test, not by eye.

### Not done here
- The same unstated encoding is in eight other files that load the knowledge
  base (`classifier.py`, `review.py`, `scope_gate.py` and others). Harmless
  while they only read ids and patterns, but a single loader is #7's fourth box.
- The buttons themselves are unit B; hard stops are unit C.

## Session 01-10-2026 — reviewer corrections, filing proposals (Bella)

### Done (merged 1 Oct)
- **#43** `POST /review/correction` → `review.record_correction()` → failure log. `/ingest`
  now returns `document_id` (SHA-256 of the bytes); only that is accepted, never a filename.
  Reason codes in `review_policy.correction_reasons`; no free text. GH#4 box 5, server half.
- **#44** `cryptography==50.0.2` pinned. Without it an owner-locked AES PDS (opens in any
  viewer) was routed as `unreadable`. Tests per failure mode. Closes GH#36.
- **#45** `storage.py`: `Storage` protocol + `LocalStorage`; never overwrites; guard test that
  `classifier.py`/`scope_gate.py`/`app.py` import no file-system libraries. GH#10 boxes 3–4.
- **#46** `filing.proposed_filename()`: `YYYY-MM-DD <abbrev>[ — <ROA situation>].<ext>`. No
  usable date → no name. GH#10 box 2.
- Issues closed: GH#12, GH#36, GH#41. GH#23 corrected to 4/5.

### Ready, awaiting merge (#47 and the list below)
- **#47** `filing.proposed_event_folder()` / `advice_subject()`: subject read from the advice
  record's scope statement, never the whole document (it reads the client's circumstances and
  the "does not cover" list). Areas in `filing_model.advice_event.subject`. Domain-approved.

- **#50** One firm-safe review level, 0.90, for every type, set once for the domain;
  `review_policy.screening_model` (screen, then confirm — the health model).
- **#51** Teach mode (#11 boxes 1–2): `settings` block; `/ingest?display=teach|off` adds the
  KB `teaching` note; independence test. Five teaching notes corrected (Bella approved).
- **#53** Bundle split counts a boundary once and names each part (fixes #52, #19 box 4).
- **#54** `approval_policy` for the review screen (roles, approvers, hard stops vs warnings,
  per-type checks) + stage map fix (PDS was in no stage; file notes in every stage).

### Decisions recorded (Bella)
- Document filename: date first, KB `abbrev` (GH#10 comment).
- Event subject: scope statement only; other areas returned as `also_mentioned` (GH#10 comment).
- Advice-event date = the **"advice as at" (commencement) date**. Expiry, meeting and
  `PDS … dated` dates are never it (GH#48).
- Review level: **0.90 for every type**, set once for all firms; no firm or user lowers it.
- Approvals: adviser or compliance only; advisers for their own clients' advice records;
  only compliance clears a hard stop (GH#54, posted on GH#4 for the review screen).
- Firm-specific document types are learned from `knowledge_base_gap` corrections (GH#23).

### Not done here
- **GH#48** — `dates.py` returns `ambiguous` on all three real SOAs: "advice as at" isn't a
  declared label, the footer date is discarded as boilerplate, `"date of advice"` is hardcoded.
  Blocks SOA folder names. In Delia's `dates.py` (GH#8). One open question back to Bella.
- **GH#10 last box** — `/ingest` returning the full proposed path + filename. Next up.
- GH#4 box 5's review-screen half waits on build step 5.

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

### Shown in the UI, and two things that fixing it exposed
- The result card renders the bundle flag: page count, the proposed ranges as
  `p1-18 + p19-24 + ...`, each boundary with its evidence and strength, and a
  line saying nothing has been split.
- **The flag renderer was keyed to one rule.** It branched on
  `determination`, which belongs to `roa_basis_unconfirmed` alone, so a
  bundle flag fell through to "The document does not say which:" followed by
  an empty list — untrue, and it hid the evidence. Now one renderer per rule
  id with a fallback that shows the question and severity rather than
  asserting something false about a rule it does not know.
- **`flagged_high_severity` is renamed `flagged_blocking`.** The name was
  accurate until a rule could override its severity's default. A medium flag
  displaying as "FLAGGED HIGH SEVERITY" is the kind of small wrongness that
  teaches a reviewer to distrust the labels. Named for what it does.

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
## Session 17-09-2026 — an unreadable file stops being a crash

### Done
- `parser.py` — `parse_pdf()` no longer raises on a file it cannot open. It
  returns the same shape either way, with `parse_error` carrying the reason,
  so no caller has to branch on whether parsing worked.
- **`/ingest` returned HTTP 500 on any unreadable PDF.** Encrypted with a user
  password, corrupt, truncated, or not a PDF at all — all of them escaped as
  an unhandled exception, and a reviewer got a stack trace where a document
  should have been. Part of #36; the two missing dependency pins in that issue
  are left for #9.
- **The same defect as #22, in a different code path** — *"a document we
  cannot read is treated the same as a document that is not advice"* — except
  worse: it was not treated as anything. `parser.py`'s own docstring already
  stated the principle it was breaking.
- **Three situations that were being collapsed, now distinct**, because a
  reviewer acts on each differently:

  | reason | meaning | what a person does |
  |---|---|---|
  | `unreadable` | nothing was read | chase the file or the password |
  | `no_selectable_text` | it opened and held no text | send it to OCR (#5) |
  | `out_of_scope` | read in full, matched nothing | confirm it is not advice |

- **A scanned Statement of Advice is still a Statement of Advice.** It was
  coming back `out_of_scope`, which is the #22 defect surviving in the review
  layer. `has_selectable_text` existed and was returned explicitly for exactly
  this purpose — nothing had ever read it.
- The catch is deliberately broad. pypdf raises `DependencyError` for AES
  without `cryptography`, `PdfReadError` for corruption,
  `FileNotDecryptedError` for a user password, and plain `ValueError`/`OSError`
  for things that are not PDFs. Enumerating them would leave the next kind of
  bad file crashing, and the response is the same for all of them: hand it to
  a person and say why.

### Not done here
- **The two dependency pins stay with #9.** `python-multipart` (without which
  the test suite cannot even be collected) and `cryptography` (without which
  every AES-encrypted PDF fails) are one line each, but they are that issue's
  subject matter and it is unassigned.
- Failing soft means the three UniSuper PDS files now route to review with a
  reason instead of crashing. They still do not get read — that needs the
  `cryptography` pin. Correct behaviour in the meantime rather than a fix.
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

## Session 17-09-2026 — verifying the classifier's confidence

### Done
- `confidence.py` — #4's third checkbox. The model's self-reported confidence
  is now checked before anything acts on it, and `/ingest` returns both
  numbers: `confidence_raw` as the model gave it, `confidence` as the system
  will act on it. `review_policy`'s thresholds are applied to the verified
  figure.
- **The number was a claim by the model about itself**, produced by the same
  process that produced the answer, and nothing independent had looked at it.
  Two things can be checked without trusting the model at all:
  - **Every phrase in `matched_signals`** is supposed to be text found in the
    document. Whether it is there is a fact about the document. The proportion
    that are becomes a multiplier.
  - **The scope gate's independent read.** It is not smarter than the
    classifier — it matches title strings — but it cannot be wrong in the same
    way a language model is wrong, and that independence is what makes
    agreement worth more than either alone. Same argument
    `filing_model.accuracy_mechanism` already makes about two axes agreeing.
- **Verification can only lower, never raise.** Accurate quoting shows the
  model told the truth about its reasoning; it does not show the answer is
  right. Letting evidence inflate a figure the model invented would launder a
  guess into a measurement. There is a test over the whole input space
  asserting the result never exceeds the raw number.
- **A silent scope gate is not disagreement.** It reads only the first 500
  characters, so a document whose title sits below that window leaves it with
  no opinion — absence of evidence, which must not be scored as evidence of
  absence.
- **An answer with no quotes at all is halved, not rejected.** No working is
  not the same as fabrication, and the flag and the review threshold should
  still see the proposal.

### The bit that was wrong first
- Matching started out whitespace-*collapsed*, and a test written against the
  real ASIC samples caught that this does not work. PDF extraction splits
  words **internally** — those files produce "A ustralian S ecurities" and
  "h is advice" — so the space sits inside the word and collapsing runs of
  spaces does not help. An accurate quote from such a page still read as
  fabricated, which would have marked down almost every real PDF and made the
  check noise rather than signal.
- Now all whitespace is removed from both sides before comparing. The cost is
  looser matching — a short signal can match inside an unrelated word, "ROA"
  sits inside "BROADWAY" — and that is tolerable **here** in a way it is not
  in `scope_gate.py`, because this only decides whether to LOWER confidence.
  A loose match declines to penalise; it never promotes anything. Recorded as
  `matching_trade_off` in the knowledge base rather than left in a comment.

### Not done here
- **The two factors are judgements, not fitted values.** 0.5 for an answer
  with no quotes, 0.6 for disagreeing with the scope gate. Nothing has been
  measured against a scored sample set because the classifier is not wired to
  one. They encode a direction and a rough weight, not an observed error rate,
  and `calibration_status` says so.
- **Nothing compares the two numbers yet.** Keeping `confidence_raw` is what
  makes model drift visible and lets the failure log show where the model was
  overconfident — but the failure log has no field for it, which is the same
  schema question raised on #12.

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
