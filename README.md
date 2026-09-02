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

Findings from a read-through of `app.py`, `parser.py`, `scope_gate.py`,
`classifier.py` and `knowledge_base.json` at `2ed1a12`. This section is deliberately notes-only: each
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

6. **Only native-text PDFs actually work end to end.** `docs/2_ARCHITECTURE.md`
   Layer 1 asks for PDF, DOCX and image-based scans, with an OCR fallback and
   scan-quality detection. Today `parse_pdf()` is `pypdf` and nothing else.
   - *Scans.* `parser.py` returns `has_selectable_text` deliberately — its
     docstring says an image-only PDF "is a flag, not silently empty input" —
     but nothing consumes it. `app.py` hands the empty string to
     `check_scope()`, which matches no title pattern and returns
     `in_scope: false`. A scanned SOA and a genuinely out-of-scope document are
     indistinguishable in the response, and both leave with no type and no
     flag. Same dead end as item 1, different cause. Scanned advice files are
     ordinary in firms: anything pre-digital, anything signed and re-scanned.
   - *Word.* A `.docx` reaching `parse_pdf()` raises inside `pypdf` and
     `/ingest` returns an unhandled 500. Fact finds and file notes are commonly
     `.docx`.

   *Steps, in the order they pay off:*
   - Make `has_selectable_text: false` a first-class outcome — a `needs_ocr`
     review reason routed to `_Needs review`, not `in_scope: false`. That is one
     branch in `app.py`, it needs no OCR to exist, and it stops the silent drop
     immediately.
   - Add an `unsupported_format` review reason alongside the magic-byte check in
     Security item 3, so a `.docx` or an image returns 415 with a reason rather
     than a 500.
   - Split `parse_pdf()` into a `parse_document()` dispatcher that selects an
     extractor from the detected type — `pypdf` for native PDF, `python-docx`
     for Word — returning one shape either way, so `check_scope()` and
     `classify()` never learn what the source format was. Same reasoning as
     Layer 6's storage abstraction.
   - Only then add OCR behind the `needs_ocr` path. Record an extraction-quality
     figure (mean OCR character confidence, or extracted characters per page)
     on the result and let it **cap** classification confidence: text recovered
     from a poor scan must never support a high-confidence auto-file. That is
     Layer 1's "detect scan quality", and it feeds item 3 above.
   - Settle one security question before OCR lands, not after: OCR usually means
     writing page images to disk. `docs/security-checklist.md` already requires
     a "quarantined temp folder" — decide now that extraction happens in memory
     or in a mode-`700` temp directory removed in a `finally` block.

7. **There is no client-identity model at all — and `client` is the outer filing
   axis.** `filing_model.axes.outer` files every document under a client, but
   `knowledge_base.json` holds no client, party or entity structure: searching it
   for `joint`, `surname`, `family`, `partnership`, `company` or `SMSF` returns
   nothing. None of the 11 `edge_case_flags` rules covers an ambiguous client
   either — `superseding_ambiguity` handles two candidate *documents*, and
   nothing handles two candidate *clients*. So the axis the whole filing tree
   hangs from has no rules behind it and no way to flag when it is unsure.

   `docs/1_PRD.md` §2.2 is explicit about what this has to survive — personal
   clients, joint clients, trusts, companies, partnerships — and names the trap
   directly: *avoid surname-only matching as a primary identity rule*. Three
   distinct failures sit behind that one line:
   - **A surname is not a client.** Two unrelated Nguyen households in one firm's
     book collapse into a single folder, and one client can see another's advice.
     That is a privacy incident, not a filing error.
   - **A family is not one client either.** John Smith, Mary Smith, John & Mary
     Smith jointly, and The Smith Family Trust are routinely four separate advice
     relationships sharing a surname — and the joint and trust documents
     legitimately name the same individuals. Grouping on surname merges all four;
     splitting on exact name string scatters documents that do belong together.
     Both directions are wrong, which is why this needs a model rather than a
     matching tweak.
   - **An entity's name need not contain its members' names.** A corporate
     trustee may appear as *Smith Super Pty Ltd ATF The Smith Superannuation
     Fund* while the SOA names John and Mary personally. Neither exact-string nor
     surname matching connects those, yet it is one advice relationship.

   *Steps:*
   - Add a `client_model` block to `knowledge_base.json` *before* any resolution
     code, per ground rule #1: `party_type` (individual / joint / trust / company
     / partnership / SMSF), a `family_key` that groups related parties without
     merging them, and the `ATF` / `ITF` / "as trustee for" patterns that mark an
     entity relationship in Australian advice documents.
   - Resolve on a **combination** of signals — full names, date of birth where
     present, address, member or account number. A surname may narrow a candidate
     set; it must never select one.
   - Return a **scored candidate set**, which is what §2.2 and Layer 3 both ask
     for. Exactly one candidate above threshold files; anything else is ambiguous
     by definition rather than by judgement.
   - Add the missing rule: `ambiguous_client`, high severity, triggering on
     multiple candidates above threshold *or* none, routed to `_Needs review`.
     This is what makes `docs/2_ARCHITECTURE.md` §4's "no silent auto-assignment
     when multiple client candidates exist" enforceable instead of aspirational,
     and it should exist before filing is wired, not after.
   - Treat joint-versus-individual as its own flag, not a resolution rule. An SOA
     naming two people may belong to a joint relationship or to one member's
     individual file; only the firm knows which. Flag it rather than guess.
   - Let `family_key` do its work at the folder level: related parties can sit
     under one family grouping in the tree while staying separate client records
     underneath. That is how firms pull files without merging identities.

### Reproducibility and audit

`docs/1_PRD.md` §2.6 requires "an audit log of every classification and reviewer
action", and ground rule #6 makes the failure log the proof of accuracy. Both
assume you can say *what produced a given decision*. Right now nothing records
that, and three separate things can change a classification without leaving a
trace.

1. **The model is a floating tag.** `classifier.py` pins `MODEL = "llama3.1"`.
   The next `ollama pull llama3.1` can fetch a different build, every
   classification shifts, and nothing in the output or the failure log says the
   engine changed. For a tool whose purpose is defending how a document was
   filed, "we can't tell you which model decided that" is the failure.
   *Steps:* record the model digest, not just the tag — Ollama's `/api/show`
   returns one; pin it in config and treat a digest change as a deliberate
   upgrade with a failure-log re-run, not an ambient event.

2. **Nothing stamps the knowledge base version onto a result.**
   `knowledge_base.json` carries `meta.version` (`0.3`) and it is, per ground
   rule #1, where every document rule lives — so a rule edit legitimately changes
   past answers. Without the version on the record, a decision made under v0.3
   is indistinguishable from one made under v0.4, and the failure log cannot tell
   "the model got worse" from "we changed the rules".
   *Steps:* return an `engine_version` block on every classification —
   `{model, model_digest, kb_version, prompt_version}` — and write the same block
   into each `failure_log.jsonl` record. `prompt_version` is a constant bumped by
   hand when `_build_prompt()` changes; a prompt edit is a behaviour change and
   should be as visible as a rule edit.

3. **Configuration is hardcoded across three files.** `OLLAMA_URL`, `MODEL` and
   the 180-second timeout sit in `classifier.py`; `TITLE_WINDOW = 500` sits in
   `scope_gate.py`. The last one is arguably a document rule and belongs in
   `knowledge_base.json` under ground rule #1 — how far into a document a title
   can appear is domain knowledge, not plumbing.
   *Steps:* move the connection settings to environment variables with the
   current values as defaults, so nothing changes for a local run; move
   `TITLE_WINDOW` into the knowledge base alongside the patterns it applies to.

4. **`knowledge_base.json` is opened three times by relative path.** `app.py`,
   `scope_gate.py` and `classifier.py` each run `open("knowledge_base.json")` at
   import. Three consequences: the app only starts when the working directory is
   the repo root, so it breaks under a service manager or any launcher that sets
   its own cwd; the same file is parsed three times; and a malformed knowledge
   base fails somewhere deep rather than at startup with a useful message.
   *Steps:* one `kb.py` that resolves the path relative to `__file__`, loads
   once, and validates the shape the three consumers rely on — that every
   in-scope document has `classifier_hints.title_patterns` — raising a clear
   error at import. Small change, and it removes a whole class of "works on my
   machine".

### State, dates and sequencing

"No flagging engine wired" reads like one unit of work in Status above. It isn't
— and the dependency is worth writing down before someone picks it up expecting
a single branch.

1. **Six of the eleven `edge_case_flags` rules cannot fire without cross-document
   state.** `app.py` is explicit that nothing is persisted; every request is
   stateless. But `roa_without_soa` triggers on "no prior SOA **on file for the
   client**", `atp_without_advice_record` on "no matching SOA/ROA **on file**",
   `fact_find_after_soa` on comparing two documents' dates, `risk_mismatch` on
   comparing a Risk Profile to an SOA, and `superseding_ambiguity` on finding two
   candidate current documents for one client. Each needs a document store *and*
   the client resolution from item 7 above — you cannot ask "for the client"
   without knowing who the client is.
   *Steps:* ship the single-document rules first — `multi_doc_bundle`,
   `advice_record_label_shift`, `no_date`, `low_confidence`, `unknown_type` need
   nothing but the document in hand, and they exercise the flag-output contract
   end to end. Give them a shared shape (`{rule_id, severity, reason, evidence}`)
   and a severity-to-routing map, so the cross-document rules later plug into a
   pipeline that already exists rather than inventing one.

2. **Nothing extracts a date, yet dates are load-bearing in three places.**
   `no_date` is a knowledge-base rule with no code behind it;
   `filing_model.advice_event.identity` keys an event on "client + advice-record
   date + subject matter"; and the naming pattern is `YYYY-MM — <subject>`. Until
   dates are extracted, advice-event grouping cannot start, and three of the
   cross-document flags have nothing to compare.
   *Steps:* extract candidate dates with their context (a preparation date, a
   signature date and a review date can all appear in one SOA), return the
   candidate set plus which one was taken as the document date and why, and fire
   `no_date` when none is found rather than defaulting to the file's mtime.
   **Parse day-first explicitly.** `03/04/2025` is 3 April in an Australian
   document and 4 March to most date libraries' defaults — a US-ordered parse
   silently reorders a client's advice history and quietly breaks
   `fact_find_after_soa`, which exists to catch advice predating its own fact
   find. This is a one-line setting that is very expensive to get wrong.

3. **Persistence, when it lands, has a design already written for it.**
   `docs/2_ARCHITECTURE.md` §3 defines Document, Client/Party, AdviceEvent,
   ReviewDecision and FailureLog, and `failure_log.py` deliberately matches its
   future SQLite `failure_log` table so it can move without a schema change.
   *Steps:* follow the same approach for the other four — SQLite, schema matching
   §3, behind a small storage module so ground rule #3's abstraction holds and
   the classifier never learns where anything is stored. Order that actually
   unblocks things: single-document flags → date extraction → client resolution
   → document store → cross-document flags → advice-event grouping. Each step is
   testable on its own; skipping ahead to grouping means building the three
   underneath it at the same time.

### Tests a fresh contributor can run, and CI

1. **A bare clone cannot satisfy the project's own pre-PR rule.** Contributing
   says `python -m pytest` must pass before opening a PR, but Run the tests notes
   most of the suite needs local `samples/` and
   `docs/sample_documents.labelling.md`, and neither is in git — correctly so,
   per File hygiene above. So the first thing a new collaborator hits is a rule
   they cannot follow until documents are transferred out of band. The fix is not
   to commit the samples; it is to make part of the suite runnable without them.
   *Steps:* add a synthetic-fixture tier. `check_scope()`, `_parse_response()`
   and `log_failure()` all take **text**, not PDFs — their tests need no client
   documents at all, only realistic strings, and `harness_demo_fixture.json`
   already sets that pattern. Split the suite so `python -m pytest` on a bare
   clone runs everything that doesn't need real documents and reports the rest as
   skipped-with-a-reason, and say in Contributing which tier is the PR gate.

2. **`tests/test_e2e.py` gates PRs on a non-deterministic LLM.** It hits Ollama
   for real, by design, which makes it the honest end-to-end check — but the same
   input can return a different answer on two runs, so a red result may mean
   nothing changed and a green one proves less than it appears to. It is also the
   slowest thing in the suite and needs a model pulled locally.
   *Steps:* mark it (`@pytest.mark.llm`), deselect it by default, and run it
   deliberately as a calibration pass over the sample set rather than as a gate
   on every change. Judge it on aggregate accuracy across the samples — with the
   `engine_version` stamp from Reproducibility above, that run becomes the record
   of whether a model or prompt change actually helped. A single-case pass/fail
   on a probabilistic component is the wrong instrument.

3. **There is no CI at all** — no `.github/` in the repo. With a public
   repository and two people merging into a `main` that is meant to stay
   runnable, CI is what makes "main always runnable" true rather than intended.
   *Steps:* one GitHub Actions workflow on pull requests that installs from the
   `requirements.txt` proposed in File hygiene and runs the no-documents-needed
   tier from item 1.

4. **Let CI enforce the file-hygiene rule mechanically.** This is the one that
   earns CI on its own. `.gitignore` protects the `docs` and `samples` *paths*;
   it does nothing about a client document added anywhere else — a repo-root
   `Example SOA.pdf`, a zip of a working folder. On a public repository that
   mistake cannot be taken back by a later commit.
   *Steps:* fail any pull request whose diff adds a `*.pdf`, `*.docx`, `*.doc` or
   `*.zip` file, with a message pointing at the docs-and-samples-outside-git
   policy in Contributing. It is a handful of lines, it runs before a human
   reviewer looks, and it converts the most expensive mistake available in this
   repo from a matter of care into a matter of configuration.

### Suggested order

Roughly by cost of being wrong, and dependencies noted where they exist:

| # | Work | Why here |
|---|---|---|
| 1 | CI document-extension gate (Tests item 4) | Cheapest item on this page and it closes the only irreversible risk |
| 2 | Case-insensitive scope gate (item 1) | One-line fix to a silent document drop |
| 3 | `needs_ocr` as a review reason (item 6) | Same silent drop, different cause; needs no OCR to exist |
| 4 | `requirements.txt` (File hygiene 1) | Unblocks CI and dependency review |
| 5 | Auth + upload limits + type check (Security 1-3) | Before the app is reachable by anything but you |
| 6 | Verified-signal confidence + threshold (items 3, 4) | Ground rule #2 needs a calibrated number to route on |
| 7 | `engine_version` stamp (Reproducibility 1-2) | Cheap now, and every later change is measured against it |
| 8 | Single-document flags, then dates (State 1-2) | Dates gate grouping and three cross-document flags |
| 9 | `client_model` + `ambiguous_client` (item 7) | Before filing writes anything to a client folder |
| 10 | Document store, then grouping (State 3) | Needs 8 and 9 first |

The three silent-drop items (2, 3, and the out-of-scope path generally) share one
root cause worth naming: the pipeline has a single exit for uncertainty,
`in_scope: false`, and it is indistinguishable from "not a document type we
handle". Everything ambiguous leaves through that one hole without a flag. Giving
uncertainty its own named outcomes is what makes ground rule #2 real.

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
