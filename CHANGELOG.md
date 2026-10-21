# Changelog

What is done, what was decided, and what is still open, so nobody redoes or
overwrites a finished step (see Contributing in `README.md`).

**How to read it**
- Newest first. Dates are `YYYY-MM-DD`. Several sessions on one day are one entry.
- Each entry uses only the headings it needs, always in this order:
  **Added · Changed · Fixed · Decided · Checked · Known gaps**.
- `#N` is a GitHub issue or PR. "Bella" is the domain collaborator; "Delia" is the engineer.
- Each line says *what* changed and *why* in a sentence. Longer reasoning lives in
  the issue, the code's docstrings, or `docs/EXPERIMENT_LOG.md`.

---

## 2026-10-21: Every decision from 21 Oct recorded in the knowledge base and docs

### Changed
- `advice_process_stages`: the six steps of the financial planning process, replacing
  engagement / discovery / construction / delivery / implementation / review. The fact
  find is in steps 2 and 3, and the SOA, ROA and PDS in step 4 (#70).
- `filing_model.stage_label`: now points to the step folders. The 9 Oct label-only
  rule is replaced.

### Added
- `filing_model.stage_folders`: `1 Goals and situation`, `2 Advice`, `3 Implementation`.
- `filing_model.file_name`: `Surname_First name_YYYY-MM-DD Type`, couples, duplicates.
- `client_model.different_surnames`, and the couple rule for file names in `joint_client`.
- `review_policy.one_click`: 90% floor for real filing (raise only), 70% for testing only.
- `docs/GROUND_TRUTH.md` "Decided 21 Oct 2026", `docs/SYSTEM.md` sections 4 and 5, and
  `CLAUDE.md` domain facts, all to match.

### Added (filing)
- `filing.client_prefix()` and the client in front of every proposed file name:
  `Nguyen_Lan_2024-03-14 SOA.pdf`, `Black_Brad_Zara_...`. No client chosen means no client
  part, never a guess.
- `filing.step_folder()` and `step_folder` / `step_reason` on every `/ingest` filing
  proposal, read from `filing_model.stage_folders`. 13 tests. 446 pass.

### Known gaps
- Placing the step folder under its event needs grouping (#8). Numbering duplicates
  (` 2`) needs the other files on hand, so it belongs to filing, not the proposal.
- To confirm with Bella: PDS and every ROA in `2 Advice`. Couples who aren't husband
  and wife: order not decided.

---

## 2026-10-21 — The client folder is proposed (#6); UI integration plan; React front end from the demo; filing by planning step decided (#70, #71)

### Added
- **Client folder on the card.** The "Would be filed as" section now fills the
  Client folder row, e.g. `Baker, George`. Still a proposal a person confirms.
- **`choose_client()`** proposes a client only when every name the document
  gives agrees. `John Smith` next to `Smith` is one client.
- **`ambiguous_client` flag (high).** Two different clients, or a joint client
  next to one of its members (`Brad and Zara Black` and `Brad Black`): no folder,
  every name listed, none chosen. The adviser picks.
- **Folder names follow Bella's rules:** `JOHN SMITH` → `Smith, John`,
  `Dr John Smith` → `Smith, Dr John`, `Anna van der Berg` → `van der Berg, Anna`,
  `Brad and Zara Black` → `Black, Brad & Zara`.
- **Entity clients:** `ABC Pty Ltd`, `Smith Family Trust` and SMSFs are filed
  under their own name. `John Smith ATF Smith Family Trust` → `Smith Family Trust`.
- 57 tests. 471 pass.
- `docs/UI_INTEGRATION.md` and `docs/ui/`: the demo's screens, what each needs
  from this backend, and the gaps. Also how the two could join and how a
  non-technical person would run it. For planning, nothing decided yet.
- `frontend/`: the demo's React screens, the latest version from
  `ahaythorpe/advice-document-classifier` (not the 10am `adf-react.zip`). Runs on
  made-up `sample-data.json` only. Not connected to the backend yet.
- `frontend/README.md`: what the page needs (the manifest), where each field
  comes from in `/ingest`, the gaps, and the steps to connect it.

### Fixed
(The 14 Oct review's client-name misses.)
- Names in capitals (`JOHN SMITH`) are found.
- `Anna van der Berg` is no longer cut to `Anna`.
- `ABC Pty Ltd`, `SMITH FAMILY SMSF` and "as trustee for" are found.

### Decided
- No folder rather than a guess when a name can't be read safely: one word
  only (`Smith`), or a joint client with two different surnames.
- The client is still not passed to the review decision. A person confirms
  the client on every document, so a proposed client mustn't make a document look safer.
- (Bella) Files go client → advice event → planning step, using the six-step
  financial planning process. Only the practical steps get folders. Replaces the
  9 Oct "stage is a label only" decision. Work tracked in #70.
- (Bella) File names start `Surname_First name_`, and couples get both first
  names. Recorded on PR #69.
- (Bella) The public demo link is switched off until the real tool is ready.

### Checked
- All 10 samples, live: `Rossi, Nick`, `Baker, George`, `Zhang, Wendy`,
  `Patel, John` (not his wife Jane), `Black, Brad & Zara`. FSGs and PDSs:
  none, "the document labels no client". No false `ambiguous_client`.
- Delia's end-to-end check on the card: _to fill in_.

### Known gaps
**For Bella:**
- Should `ambiguous_client` block Approve, or warn? A warning for now (`not_yet_decided`).
- Are the titles, surname particles and entity-marker lists right? All marked
  "proposed, not yet confirmed".
- Joint folders keep the document's name order, because a name doesn't say who
  the husband is (`joint_client.order`).
- How should a joint folder be named when the two surnames differ?

**Not built:**
- Matching on DOB, address or account number, and `family_key`. These need a
  firm client list to match against, and none exists.
- No real sample names a trust or company client, so entity handling is tested
  on made-up names only.
- `MCDONALD` becomes `Mcdonald`. Names the document writes in mixed case are kept as written.
- Letting a firm set its own naming and filing rules through a chat box: ideas
  in #71, after the filing basics.
- The React page has no Edit, no failure-log verdicts and no display mode. The
  current `static/index.html` has all three, so it stays until they carry over.

---

## 2026-10-20 — README rewritten for two audiences; every result names its engine (#7)

### Added
- **`engine_version` on every `/ingest` result:** model, model digest, Ollama
  version, knowledge-base version and prompt version. The tag `llama3.1` names
  whatever was last pulled, so a pull could change every answer with no line of
  this repo changing. The digest names the exact weights.
  - Read from Ollama for every document, not once at startup: Ollama updated
    itself during the #59 experiment while the app kept running.
  - `prompt_version` is a hash of the prompt and hints, so editing either one
    changes it without anyone bumping a number.
  - If Ollama can't be asked, values are `None` and `engine_version_error` says why.
- **`failure_log.jsonl` records carry the stamp.** The page sends back the stamp
  of the proposal being judged, not whatever is running when someone clicks.
  Exactly five fields, identifier characters only, so no free text can be written.
  Lines written before today have no stamp.
- `kb.py`: one loader for `knowledge_base.json`. It finds the file next to
  itself, reads UTF-8, and stops at startup naming any missing section.
- `config.py`: `OLLAMA_URL`, `OLLAMA_MODEL` and `OLLAMA_TIMEOUT` env vars. The
  defaults are the old hardcoded values, so nothing changes unless you set one.
- 21 tests. 414 pass.

### Changed
- `README.md` now opens with a plain-language section for finance and accounting
  readers (the problem, what the tool does, what it never does, why it matters),
  then a status summary, then a shortened quick start. Contributor detail moved
  under one "For contributors" heading.
- Nine modules import the knowledge base from `kb.py` instead of each opening it.
- `TITLE_WINDOW` (500) moved from `scope_gate.py` into the knowledge base's new
  `scope_gate` section, with its reason (ground rule #1).
- `failure_log.py`'s record has a seventh field, `engine_version`; the
  exact-field test was updated deliberately.

### Fixed
- **The model was sent garbled hints on Windows.** Eight of nine modules read
  the knowledge base without UTF-8, so `—` reached the classifier as `â€”`. Two
  tests passed only because they garbled it the same way; they now read UTF-8 too.
- The app no longer depends on the folder it is started from to find the knowledge base.
- `classify()` keeps Ollama's own error text. A missing model now says
  "model '…' not found, try pulling it first", not only "404 Client Error".
- README no longer says `docs/` is missing. The docs map lists the files that
  actually exist (it named `SYSTEM_v2.md` and `ARCHITECTURE_TRACE.md`, which
  don't, and left out `GROUND_TRUTH.md`, `EXPERIMENT_LOG.md` and
  `advice_classification_reference.md`).
- References to `docs/TO_DO_LIST.md`, which isn't in the repo, are removed.
- The project layout lists every module, including `clients.py`, `confidence.py`,
  `dates.py`, `display.py`, `filing.py`, `flags.py`, `review.py` and `storage.py`.
- "What's next" now includes #66.

### Decided
- `config.py` holds the env vars, not `classifier.py`. `tests/test_storage.py`
  bans `os` in classification code as its marker for file access (ground rule
  #3). Env vars aren't storage, and loosening the guard would let paths in too.
- The digest comes from Ollama's `/api/tags`. #7 said `/api/show`, which returns
  no digest (checked against Ollama 0.40.6).

### Checked
- Live: `ROA_INFO266_att2` → `roa`, stamped `llama3.1` / `46e0c10c…` / Ollama
  `0.40.6` / KB `0.3` / prompt `208f9650f7f8`. Approve wrote the same stamp to the log.
- With `OLLAMA_MODEL=nope`, the stamp reads `nope:latest is not pulled on this Ollama`.

### Known gaps
- `app.py` still finds `static/` relative to the starting folder, so the app
  must be started from the repo. Fixing it needs `pathlib` in `app.py`, which the
  storage guard forbids, so it needs its own decision.
- `multi_doc_bundle.leading_region_chars` (500) duplicates
  `scope_gate.title_window_chars`; they must be kept equal by hand.
- `docs/2_ARCHITECTURE.md`'s planned `failure_log` table has no `engine_version` column yet.
- The stamp isn't shown on the result card, only in the response and the log.
- Who made a verdict or a rename (`filing_model.renaming`) needs logins
  (`approval_policy`), not #7. Move it to its own issue.

---

## Classifier evidence as exact quotes 

### Changed
- `classifier.py` prompt: `matched_signals` must be 3–6 short quotes (3–8 words)
  copied exactly from the document text. Never a summary, a field label or a hint.
  The hints are labelled "NOT text to quote", and the document text comes last.
- The prompt's concrete example quotes are gone: the model copied `"Our fees are $3,300"` into four documents.
- `classify()` sends `temperature: 0`, so the same document always gets the same
  answer. Without it, scores for one file varied by 20–44 points (part of #7).

### Added
- `tests/test_classifier.py`: 3 tests. The prompt keeps the exact-quote
  instruction, the document text comes last, and temperature is sent as the
  number `0` (Ollama rejects `"0"`). 393 tests pass.
- `docs/EXPERIMENT_LOG.md`: every run, score and finding behind this change.

### Checked
- **INFO 267: 0.41 → 0.90 (passes).** Every quote was found in the text.
- **FSG_UniSuper: 0.45 → 0.40 (doesn't pass).** Its quotes are real text that PDF
  extraction splits across two columns. A prompt rule tried for this made things worse and was reverted (log findings 10–11).
- Every sample kept its correct type. `confidence.py` unchanged.

### Known gaps
- Multi-column PDFs need column-by-column text extraction (#5).
- For #7: stamp the model digest and Ollama version on results (Ollama updated
  itself mid-experiment). `classify()` discards Ollama's error message.
  `classifier.py` opens the knowledge base without UTF-8, so em dashes reach the model garbled.

---

## 2026-10-14 — Client name format; next fixes from Bella's code review

### Decided
- (Bella) Folder names use normal capitals and keep titles after the comma:
  `JOHN SMITH` → `Smith, John`, `Dr John Smith` → `Smith, Dr John`.
  Recorded as `client_model.name_format`; not built yet (#6).

### Known gaps
(Bella's review of the code, 14 Oct. Nothing here is built; each is its own branch + PR for Delia.)
- **Client names (`clients.py`, #6):** `JOHN SMITH` (all capitals) is not found;
  `Anna van der Berg` is cut to `Anna` (van, der, de, von dropped); `ABC Pty Ltd` is
  not found, though companies, trusts and SMSFs are clients (`entity_client`);
  `Mr John Smith` should give `Smith, Mr John` (`name_format`).
- **Dates (`dates.py`, #48):** two different "Date of advice" dates silently picks the
  first; it should go to a person. `03/04/24` (two-digit year) is ignored.
- **"date of advice" is written in `dates.py`:** move it to `knowledge_base.json` (ground rule 1).
- **INFO 267 subject:** "want advice about" matched a negated sentence. Skip negated
  sentences or prefer the "Scope of my advice" section. Correct answer: Personal Insurance.
- **Who did it:** `/review/correction` records no reviewer, which "show who renamed it"
  needs (`filing_model.renaming`, #7).
- **Confirm everything:** a person confirms type, client, stage and name on every
  document (`review_policy.certainty_decision`). Agree the screen with Bella before
  changing the 0.90 thresholds.
- **Tidy:** stale comments in `app.py` ("no classifier yet", a duplicated comment) and
  `.github/workflows/tests.yml` ("docs/ gitignored"); the skip message in `conftest.py`
  points to a README heading renamed 13 Oct; `harness.py` still needs `sample_documents.json`.

---

## 2026-10-13 — `docs/` added and corrected 

### Added
- (Delia) The eight handover documents in `docs/`: `SYSTEM.md`, `1_PRD.md`,
  `2_ARCHITECTURE.md`, `3_BUSINESS_CASE.md`, `HANDOVER.md`, `GROUND_TRUTH.md`,
  `advice_classification_reference.md`, `sample_documents.labelling.md`. The
  partner's name is replaced with "the domain collaborator". Samples stay out.

### Fixed
(Bella: several were 20 Aug copies from before later decisions.)
- `advice_classification_reference.md` replaced with the 29 Sep version: **three** ROA situations, not four.
- INFO 266 attachment 2 is **further advice** recommending no change. Fixed in
  `HANDOVER.md` and `sample_documents.labelling.md`.
- Small investment is s946AA + reg 7.7.09A, not reg 7.7.10AAA.
- "Four bases" → three situations in `1_PRD.md`, `2_ARCHITECTURE.md`, `3_BUSINESS_CASE.md`.
- "11 flag rules" → the rules in `edge_case_flags` (12 today). The ROA flag id is `roa_basis_unconfirmed`.
- `SYSTEM.md`: event folder is `YYYY-MM — subject`, never labelled `[SOA]`; stage shown per document.
- `GROUND_TRUTH.md`: folder levels, joint clients (Q1) and sub-folders (Q6) marked answered 9 Oct.
- `CLAUDE.md` and `README.md` no longer say `docs/` is missing.

### Decided
(Bella, #61 Q2–Q4, Q7, Q8. Recorded in `knowledge_base.json` and `GROUND_TRUTH.md`; no code reads them yet.)
- **Trust, SMSF, company** is the client, with its own folder (`client_model.entity_client`).
- **Same surname:** `Surname, First name` tells clients apart (`client_model.same_surname`).
- **Several names:** file under the shared surname, or under the trust if a
  trustee is named. Otherwise flag and ask the adviser (`client_model.several_names`).
- **100% certainty** on document type, client name, advice stage and new name.
  A wrong one risks compliance fines. A person confirms every document; nothing
  files automatically (`review_policy.certainty_decision`). Thresholds not changed yet.
- **Renaming** documents and folders is allowed, tracking who, when, old and new,
  with the renamer shown (`filing_model.renaming`, needs #7).
- **Joint folder order:** husband's first name first (`client_model.joint_client.order`).
- **INFO 267's subject is Personal Insurance.** Its "Scope of my advice" (p7)
  excludes super. The tool said *Superannuation* because "want advice about"
  matched p2's "John did **not** want advice about his superannuation". **For
  Delia:** scope phrases must ignore negated sentences, or prefer a "Scope of my
  advice" section. Not changed yet.
- **Spouse named but not the client** (INFO 267's Jane): the folder uses the client's name only (`client_model.several_names.spouse_named_not_client`).
- **Other documents firms hold** (#23): emails, government outcome letters,
  invoices, ID, tax returns, provider forms. Listed in the docs; not document types yet.

---

## 2026-10-09 — Event folders name the event; issues brought up to date

### Changed
- **The event folder is named after the event, not one document:**
  `2021-10 — Superannuation & Insurance`, no `[SOA]` (#58). The folder holds every
  document of the event. The record type and ROA situation stay in each
  **filename** (`2021-10-12 ROA — further advice.pdf`). `naming_note` in the KB says why.
- **The advice stage is shown per document, not as a folder.** `filing_model.stage_label`;
  `filing.advice_stages()` reads `advice_process_stages[].typical_docs`. An SOA reads
  `3 Advice construction · 4 Advice delivery`; a file note reads `Any stage`. The result
  card has an "Advice stage" row. Stage folders were ruled out: an event usually holds
  one or two documents per stage.
- `proposed_event_folder()` no longer takes `flags`. It only used them for the tag.
- **`.gitignore` no longer ignores `docs`.** It had done so since the first commit, so
  the spec was never in the repo. Client files stay blocked by the `*.pdf`, `*.docx`,
  `*.doc` and `*.zip` rules and by `samples`. `README.md` and `CLAUDE.md` updated.

### Added
- `tests/test_filing.py`: `proposed_filing()` tests, plus stage tests for every
  type. 359 non-LLM tests pass (344 before), 13 skipped.
- New issues: #59 (exact-quote evidence; INFO 267 49%, FSG_UniSuper 32%), #60
  (missing `docs/`), #61 (every domain question for Bella).

### Decided
- (Bella) **Joint client → one shared folder**, e.g. `Black, Brad & Zara` (`client_model.joint_client`; #6, #61).
- (Bella) **A PDS with blank application forms appended is separate documents.**
  The bundle flag on `PDS_AustralianSuper` is right; a person splits it (#19).

### Checked
- Closed #10. Its last item, the full path with a client folder, moved to #6.
- Status lines refreshed on #2, #5, #6, #7, #8, #11, #19, #20, #23, #26 and #48.

### Known gaps
- The client folder stays empty until #6 slice 3 chooses a client.
- Stages stay at six. FPSB's seven-stage split was not adopted.
- Next for Delia: #59, then #48 (SOA dates), then #6 slices 2–3.

---

## 2026-10-08 — Proposed filing shown on ingest (#10)

### Added
- `filing.proposed_filing()` reads the document's date once and passes it to the
  existing `proposed_filename` and `proposed_event_folder`. It returns client
  folder, event folder, filename and date, each with a reason when it can't be
  filled. It joins existing functions; it adds no naming logic.
- `/ingest` returns a `filing` block. **A proposal only:** nothing is written or
  moved, and `storage.py` isn't called. The parts aren't joined into one path,
  because with no client folder a joined path would look like a real destination.
- The result card has a **"Would be filed as"** section. A part that can't be
  filled reads *none* plus its reason, never a blank. Restart the server to see it.

### Checked
(By hand, classifier stubbed. 375 non-LLM tests pass.)
- `ROA_INFO266_att1` → `2021-10 — Superannuation & Insurance` / `2021-10-12 ROA — further advice.pdf`.
- `SOA_INFO267` → `2021-10-22 SOA.pdf`. Right: the model's "December 2021" is when
  ASIC published INFO 267, and filing doesn't use the model's date.
- `ROA_INFO266_att2` → `2021-08 — Retirement & Investment` / `2021-08-30 ROA — further advice.pdf`.
- `SOA_RG90` → no name and no folder, because the date is ambiguous. That's #48, not a filing bug.

### Known gaps
- No client folder until #6 slice 3.
- Accepting a proposal doesn't file anything: `storage.put` has no caller, and no filing root is configured.
- INFO 267 scored 49% for a correct SOA: half its "quotes" were the model's own summaries. Same cause as FSG_UniSuper on 2 Oct → #59.

---

## 2026-10-06 — Finding the client's name (#6 slice 1)

### Added
- `clients.py` (17 tests): `find_client_candidates(pages)` returns every name a
  document labels as its client, with the label, page and context. **It finds; it doesn't choose.** Choosing is slice 3.
- `knowledge_base.json` `client_model.name_labels`: `client name`, `account name`,
  `soa for`. Only labels a real sample uses. Adding one is a KB edit, not Python.
- `/ingest` returns `client_candidates`, and the card shows each name. **Shown, not
  used:** `review.assess()` doesn't see it, and a test pins that.

### Fixed
(Where a name ends.)
- The next PDF column lands on the same line, so capitalisation alone took `John Patel The`.
- A column gap ends a name only once it has two words (`Account name: Wendy ⟶ Zhang`).
- A following field (`Account number:`) ends a name. A wider rule had cut `Wendy Zhang` to `Wendy`.
- A test expected no name from RG 90, but its example SOA names Brad and Zara Black
  in every header. Fixed by adding the `soa for` label, not by loosening the rule.

### Checked
- All 10 samples: four advice records give Nick Rossi, George Baker, Wendy Zhang and
  John Patel. RG 90 gives `Brad and Zara Black`, a joint client kept whole. The FSGs
  and PDSs give none, which is correct. Advisers and INFO 267's wife Jane are not returned.

### Known gaps
- Slice 2 (party type: person, trust or company) and slice 3 (choose one client).
  Until slice 3, the 90% rule is only half enforced.
- No firm client list exists to match against.
- Known misses, which fail safe (nothing found → a person): `JOHN SMITH` in capitals and `Smith, John`.
- Only the 10 local samples were run. The RG 90 2013 SOA may need a `statement of advice for` label.

---

## 2026-10-02 — Review screen: the choices, and Approve / Reject

### Added
- `GET /review/options`: document types and reason codes read from the KB, so the
  page keeps no copy (ground rule 1). Approve sends `confirmed`; Reject picks one
  of five codes; there is no free text. 5 tests.
- **Approve / Reject on every result card.** Reject asks *what it actually is* and
  *why*, and Submit stays disabled until both are picked. A recorded verdict reads
  "Recorded … Nothing has been filed." Out-of-scope cards get Reject only. A
  "classifier unavailable" card gets no buttons, because a runtime failure isn't a
  verdict on the document. Buttons are disabled while a verdict is being sent, so a double click records once.
- `tests/test_review_buttons.py`: 16 tests on the server side of every click.

### Fixed
- `app.py` opens the knowledge base as UTF-8. On Windows, cp1252 had garbled every em dash. Found by a test.

### Checked
- Approve on `FSG_PeninsulaWealth.pdf` wrote one `reviewer:confirmed` line, keyed
  by SHA-256 with no filename.
- "WinError 10061" means Ollama isn't running. Check that `http://localhost:11434` reads "Ollama is running".

### Known gaps
- Whether each verdict is *right* is a domain call, handed to Bella.
- `FSG_UniSuper` scored 0.32 because the model returned field labels as quotes → #59.
- No roles yet, so anyone can approve. `approval_policy` (#54) needs a login first.
- The same unstated encoding is in the other KB loaders, including `classifier.py` → #7.

---

## 2026-10-01 — Reviewer corrections, filing proposals (Bella)

### Added
- **#43** `POST /review/correction` writes a reviewer's verdict to the failure log,
  keyed by `document_id` (SHA-256 of the bytes), never a filename. Reason codes only, no free text.
- **#45** `storage.py`: a `Storage` protocol and `LocalStorage`; never overwrites.
  A test checks the classifier never imports file-system code.
- **#46** `filing.proposed_filename()`: `YYYY-MM-DD <abbrev>[ — <ROA situation>].<ext>`. No usable date → no name.
- **#47** `filing.proposed_event_folder()`: the subject is read from the advice record's scope statement only.
- **#51** Teach mode: a `settings` block; `/ingest?display=teach|off` adds the KB's
  `teaching` note. Five teaching notes corrected.
- **#54** `approval_policy`: roles, approvers, hard stops vs warnings. Also a
  stage-map fix: the PDS was in no stage, and file notes are now in every stage.

### Changed
- **#50** One review level, **0.90 for every type**, set once for all firms (`review_policy.screening_model`).

### Fixed
- **#44** `cryptography` pinned. Owner-locked AES PDFs were routed as `unreadable`. Closes #36.
- **#53** A bundle boundary is counted once, and each part is named. Fixes #52.

### Decided
- Filename: date first, then the KB `abbrev`.
- Event subject: from the scope statement only. Other areas come back as `also_mentioned`.
- The advice-event date is the **"advice as at" (commencement) date**. Expiry,
  meeting and `PDS … dated` dates never are (#48).
- Approvals: adviser or compliance only. Advisers approve their own clients'
  records. Only compliance clears a hard stop (#54).
- Firm-specific document types are learned from `knowledge_base_gap` corrections (#23).
- Issues closed: #12, #36, #41. #23 corrected to 4 of 5.

### Known gaps
- **#48:** `dates.py` returns `ambiguous` on all three real SOAs, which blocks SOA folder names.
- #4 box 5 (the review-screen half) waits on build step 5.

---

## 2026-09-24 — Date extraction (#8); #9 finished properly

### Added
- `dates.py` (23 tests), in four units:
  - `find_date_candidates`: date-shaped text with page and context.
  - `parse_day_first`: `03/04/2025` is 3 April. Rejects invalid dates and 2-digit years.
  - `select_date`: returns `declared`, `inferred`, `ambiguous` or `absent`.
  - `extract_dates(parsed)`: runs on `parser.py`'s real output.
- An `llm` test marker, deselected by default (`pytest.ini`), so bare `pytest` no
  longer needs Ollama. `pytest -m llm` runs the live test.
- A file-hygiene CI job that fails any PR adding `*.pdf`, `*.docx`, `*.doc` or `*.zip`.

### Fixed
- Two mentions of the same date counted as competing dates, which made 2 of 3 FSGs
  `ambiguous`. Candidates are now grouped by date value. Across the 10 samples:
  3 declared, 3 inferred, 4 genuinely ambiguous.

### Checked
- On real samples, a bare `Month YYYY` is a template stamp, never the advice date. The regex was right to skip it.

### Known gaps
- `extract_dates()` isn't wired into `/ingest`, and nothing fires the `no_date` flag yet.
- No hand-labelled expected dates exist for the samples.

---

## 2026-09-22 — CI workflow

### Added
- `.github/workflows/tests.yml` runs `pytest -rs` on every PR and every push to
  `main`, on Python 3.10 and 3.12, with no Ollama and no samples. `-rs` prints why each test was skipped.
- `requirements-dev.txt`: runtime dependencies plus `pytest` and `httpx`, pinned.

### Fixed
- `requirements.txt` was missing `python-multipart`, so `import app` failed in a fresh
  environment. Pinned at `0.0.22`. Found by installing into an empty virtualenv.

### Known gaps
- The workflow hadn't run on GitHub yet, and Python 3.10 couldn't be tested locally.
- `main` is not protected, so CI reports failures but blocks nothing.

---

## 2026-09-21 — CI test tiers

### Fixed
- A bare clone no longer fails. Tests needing `samples/` were failing with
  `FileNotFoundError`. Now: 0 failed, 60 passed, 7 skipped.

### Added
- `@pytest.mark.samples` marks the 25 tests that read real PDFs. `conftest.py`
  skips them with a reason when `samples/` is empty.

### Known gaps
- A partly filled `samples/` folder still fails on the missing file, on purpose.
- `test_e2e.py`'s sample tests weren't run: they need `llama3.1`, and this machine had `qwen2.5:3b`.

---

## 2026-09-17 — Confidence check, review threshold, flags, bundles, fail-soft parsing

### Added
- **Confidence check** (`confidence.py`): verified confidence = the model's
  confidence × quotes found × scope-gate agreement. `/ingest` returns both
  `confidence_raw` and `confidence`; thresholds apply to the verified figure.
  - It only ever lowers the number. Accurate quotes show the model was honest, not that it was right.
  - A silent scope gate isn't disagreement.
  - An answer with no quotes is halved, not rejected.
- **Review threshold** (`review.py`): every document gets a `review` block saying
  whether it needs a person and why. Thresholds moved from `static/index.html` into
  `review_policy` in the KB. (They were per type then; they became one 0.90 on 1 Oct.)
  - Out of scope, `unknown_type` and `classifier_unavailable` are separate reasons.
  - A low-confidence document keeps its working.
  - Reasons accumulate rather than stopping at the first.
- **ROA basis flag** (`flags.py`): `evaluate_flags()` reads `edge_case_flags`, and
  `/ingest` always returns `flags`. `roa_basis_unconfirmed` (medium) fires on every ROA.
  - It proposes a situation when the text supports exactly one, otherwise
    `ambiguous` or `absent`. A declared basis beats an inferred one.
  - Every rule declares `stateless` or `stateful`, and the engine runs only stateless rules.
- **Bundle detection** (#19 boxes 2–3): `multi_doc_bundle` fires on a "page 1 of N"
  restart, or on a change from one document type to another. **Nothing is ever split.**
  Page ranges go to a person. `multi_doc_bundle` forces review; `roa_basis_unconfirmed` doesn't.
- **Fail-soft parsing** (`parser.py`): `parse_pdf()` never raises, and `/ingest` no
  longer returns HTTP 500 on a bad PDF. Three reasons replace the crash:

  | reason | meaning | what a person does |
  |---|---|---|
  | `unreadable` | nothing was read | chase the file or the password |
  | `no_selectable_text` | it opened and held no text | send it to OCR (#5) |
  | `out_of_scope` | read in full, matched nothing | confirm it isn't advice |

- **Failure-log corrections** (#12): an optional `corrections` list of `{kind,
  predicted, correct}`. The kinds are `doc_type`, `roa_situation` and `confidence`.
  There is no free-text field, so a client name has nowhere to go.

### Changed
- **Three ROA situations, not four** (#33). `legislation.four_kinds` became
  `situations`; `hold_no_action` was absorbed into `no_buy_sell`. "Hold" is what the
  advice recommends, not a basis. `CLAUDE.md`, `flags.py` and tests updated.
- `flagged_high_severity` renamed `flagged_blocking`: a rule can now override its severity.
- The flag renderer has one view per rule, with a fallback. It had been built around the ROA flag only.

### Fixed
- **Quote matching** removes all whitespace before comparing. PDF text splits words
  internally ("A ustralian S ecurities"), so collapsing spaces wasn't enough. Looser
  matching is acceptable here because it can only decline to lower a score.
- **ROA flag on INFO 266 att 1** first said `ambiguous`. "Retain your existing
  policy" describes a consequence, not a hold, and "no changes to one fund" inside
  advice that changes another isn't a no-action ROA.
- **Bundles:** suppressing types that appear on most pages hid real boundaries. The
  `pds → risk_profile → pds` excursion rule needed both of its halves.

### Checked
- Bundle detection across 25 files: no mismatches, 5 genuine bundles.
  - The CP 284 (p56) and RG 90 2013 (p40) SOAs carry an appended ATP.
  - `PDS.pdf` is an AustralianSuper PDS with five forms appended.
- The sample set covers one ROA situation (further advice) three times.

### Known gaps
- The confidence factors (0.5, 0.6) and thresholds are judgements, not measurements (`calibration_status`).
- Five stateful flags wait on persistence (#8).
- Nothing writes a correction yet. That needs the review screen (#4 box 5).
- No flag fires end to end without Ollama, because flags key on the classified type.
- ASIC's 2021 media release mentions "four exemptions". Kept as `unresolved` in the KB.

---

## 2026-09-10 — File notes; stage references

### Added
- The `file_note` document type, listed in stage 3. Data only, no Python. It's the
  only paper trail for safe-harbour steps 3–6.
  - Without it, a meeting note came back as a PDS.
  - Notes often record a call to a *provider*, so a fund's name in the title says who was contacted, not who issued the note.
  - `advice_record_role: false`.
  - Seven scope-gate tests.

### Fixed
- Stage 6: `ongoing_fee_consent` → `fee_disclosure_statement`. `annual_review` removed: it's a service event, not a document.

### Known gaps
- `.docx` returns HTTP 500, and file notes are usually Word documents (#5).
- `application_forms` is a genuine missing type (#23).

---

## 2026-09-05 — Dependencies, type set from the KB, scope-gate fixes

### Added
- `requirements.txt` pinned, with a Python 3.10 floor.
- The failure-log de-identification rule, and a test on its exact field set (#3).
- `.gitignore` blocks client documents by extension anywhere in the tree.
- `parse_pdf()` returns per-page text (#19). `"\n".join(pages) == extracted_text` always holds.

### Changed
- The supported document types come from `knowledge_base.json`. They were
  hardcoded in three files (#12).
- The `car` type was removed: DBFO Tranche 2 isn't law. `advice_record_role` keeps the transition seam.
- The ATP's hints key on what it does (a client's grant of authority to the
  adviser), not on its title, which firms word inconsistently.

### Fixed
- The scope gate ranks by earliest match, not by pattern length. An ROA citing a PDS had come back as a PDS (#4).
- Case sensitivity is decided per pattern, so ALL-CAPS cover pages match while acronyms stay strict (#4).
- Patterns match on word boundaries. "ROA" had matched ROAD and BROADWAY (#12).
- `test_parser.py` builds its PDFs in the test, so it runs on a bare clone.

---

## 2026-08-31 — Starting point

### Added
- Live app: `parser.py` (pypdf), `scope_gate.py`, `classifier.py` (local Ollama
  `llama3.1`, grounded in `classifier_hints`), `app.py` (`POST /ingest` plus a
  drop-zone page) and `failure_log.py` (JSON Lines). 40 tests.
- Harness: `knowledge_base.json` v0.3, and `harness.py` (a keyword matcher, run on a synthetic fixture).

### Known gaps
- At this point there was no filing, no flag engine and no Approve/Edit/Reject screen.
- `docs/SYSTEM.md` and `SYSTEM_v2.md` were not yet reconciled.
- Undecided: does `harness.py` stay as an offline tester alongside the live app?
