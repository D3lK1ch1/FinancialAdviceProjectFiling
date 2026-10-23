# Advice Document Classifier & Filing System

A tool that reads a financial-advice firm's client documents, works out what each
one is, and suggests where to file it. A person approves every suggestion.

Public demo of where this is heading: **https://advice-document-classifier.vercel.app**
(built from [`ahaythorpe/advice-document-classifier`](https://github.com/ahaythorpe/advice-document-classifier)).
This repo takes that demo from pilot towards a working product.

- **New to the project, or from finance/accounting?** Read [Why this exists](#why-this-exists) and [Where it stands](#where-it-stands).
- **Reviewing or testing it?** Go to [Quick start](#quick-start).
- **Contributing code?** Read [For contributors](#for-contributors) and `CLAUDE.md`.

---

## Why this exists

Australian financial-advice firms hold many regulated documents for each client:
Statements of Advice (SOA), Records of Advice (ROA), Financial Services Guides
(FSG), Product Disclosure Statements (PDS), fact finds, risk profiles, fee
consents and more. Under the Corporations Act, firms have to keep these records
and be able to produce the right one when asked.

Today, staff file them **by hand**. The main advice platforms *store* documents,
but none of them *reads* a document and says "this is an ROA for this client,
from this advice event". When filing goes wrong, the firm loses time and runs a
compliance risk: if a record can't be found, the firm can't show the advice was
properly documented.

**What this tool does for a firm:**

| Step | What happens |
|---|---|
| 1. Read | Takes a PDF and pulls out its text. |
| 2. Identify | Decides which of 11 document types it is (SOA, ROA, FSG, PDS, Authority to Proceed, provider form, Fact Find, Risk Profile, File Note, Fee Disclosure Statement, Ongoing Fee Consent) and quotes the exact words that gave it away. |
| 3. Check | Raises compliance flags. For example, an ROA is only allowed in three specific situations, so the tool asks someone to confirm which one applies. |
| 4. Propose | Suggests a folder (client → advice event) and a standard file name. |
| 5. Ask a person | Shows how confident it is. A staff member approves or rejects. Anything uncertain goes to a "Needs review" pile with the reason. |

**What it deliberately does not do:**
- **It never files anything on its own.** Every document is a proposal that a person confirms. A wrongly filed client record is a compliance problem, so the bar is certainty, not "probably".
- **It never writes or recommends financial advice.** It only describes documents that already exist.
- **It is not legal advice.** The document rules are mapped to the legislation and ASIC guidance to drive classification, and they still need sign-off from a professional.

**Why it matters:** advice practices are small (around 2.5 advisers on average)
and cost-squeezed, and the planned move from SOAs to Client Advice Records will
make every firm rework its record-keeping. An advice-specific filing assistant
that sits on top of existing systems, rather than replacing them, fills a gap
nobody currently covers. The full case is in `docs/BUSINESS_CASE.md`.

---

## Quick start

Works on **macOS** and **Windows**. Use **Terminal** on a Mac and **PowerShell** on Windows.

**You need**
- **Python 3.10+.** Check with `python3 --version` (Mac) or `python --version` (Windows). Get it from [python.org](https://www.python.org/downloads/).
- **[Ollama](https://ollama.com/download)**, which runs the AI model locally. Install it like any app.
- **The `samples/` folder**, from Delia directly. It is not in git (see [Client documents and samples](#client-documents-and-samples)). You can run the app without it; you just won't have test documents.

**One-time setup**

```
git clone https://github.com/D3lK1ch1/FinancialAdviceProjectFiling.git
cd FinancialAdviceProjectFiling
```

| | Mac | Windows |
|---|---|---|
| Create environment | `python3 -m venv .venv` | `python -m venv .venv` |
| Activate it | `source .venv/bin/activate` | `.venv\Scripts\activate` |

Your prompt now starts with `(.venv)`, and `python` works the same on both systems.

```
python -m pip install -r requirements.txt
ollama pull llama3.1          # about 5 GB, once
```

On a Mac, the first `git` command may offer to install "command line developer
tools". Accept, then run the command again.

**Each time**

1. Open the Ollama app. Check that **http://localhost:11434** says "Ollama is running".
2. Activate the environment (table above), then run:
   ```
   python -m uvicorn app:app --port 8000
   ```
3. Open **http://127.0.0.1:8000/** and drop a PDF on the page. Or open
   **http://127.0.0.1:8000/app/** for the new screens. Build them once first
   (`frontend/README.md`).
4. Stop with `Ctrl+C` (also `Ctrl` on a Mac, not `Cmd`).

**"Couldn't reach the classifier … connection refused"** (`WinError 10061` /
`Errno 61`) means Ollama isn't running. This has nothing to do with Wi-Fi. Start
Ollama and drop the file again. The first document after a few idle minutes can
take about a minute while the model loads.

## Reviewing a document

Each result card ends in **Your verdict**. Nothing is filed or moved. Your
verdict is **recorded** so the tool's accuracy can be measured.

- **Approve**: the document type is right.
- **Reject**: it's wrong. Pick **what it actually is** and **why**:

  | reason | when |
  |---|---|
  | lookalike | it quotes or resembles another type (e.g. an SOA that refers to a PDS) |
  | non standard title | its title is missing, firm-branded or unusual |
  | poor text | the text was garbled or incomplete (scan, image-heavy page) |
  | bundle | one file holds more than one document |
  | knowledge base gap | none of the above: a rule is missing |

  There is no free-text box, on purpose: typed notes are where client names leak in.
- A "Not recognised" document offers Reject only.

Each verdict becomes one line in `failure_log.jsonl`, recorded against a
fingerprint of the file's contents, never its name. **When you finish a review
session, send `failure_log.jsonl` to Delia.** Those lines are how the tool's
accuracy is checked against reality.

---

## For contributors

**Read `CLAUDE.md` first.** It holds the ground rules: the knowledge base is the
source of truth, nothing files silently, storage stays abstracted, and work
lands on a branch and goes through a PR. If your change conflicts with it, raise
that before opening the PR, not after.

### How a document flows through

`POST /ingest` in `app.py`, in order:

1. **`parser.py`** extracts text with `pypdf` in layout mode.
2. **`scope_gate.py`** checks the first 500 characters against the knowledge base's title patterns. It is deterministic, with no AI involved.
3. **`classifier.py`** runs only when the document is in scope. It sends the text and every type's hints to local Ollama `llama3.1` at temperature 0, and gets back `{doc_type, confidence, matched_signals}`.
4. **`confidence.py`** checks the model's claim: are the quotes really in the text, and does the type agree with the scope gate?
5. **`flags.py`**, **`clients.py`**, **`review.py`**, **`filing.py`** and **`display.py`** add the compliance flags, found client names, the review decision, the filing proposal and the teaching text.

Nothing is persisted. Each request goes PDF in, JSON out.

### Project layout

```
app.py              FastAPI app: POST /ingest, POST /review/correction, GET /review/options
parser.py           PDF -> text + metadata
scope_gate.py       deterministic in-scope check from title patterns
classifier.py       LLM classification via local Ollama
confidence.py       verifies the model's quotes and confidence
flags.py            compliance flags (edge_case_flags in the knowledge base)
clients.py          finds client names labelled in the document
dates.py            advice-date extraction
review.py           review decision + recording verdicts
filing.py           proposed folder and file name
storage.py          storage seam: local folder now, cloud later
display.py          teaching mode
failure_log.py      de-identified verdict log (failure_log.jsonl)
static/index.html   drop-zone UI served at /
knowledge_base.json document types, hints, flags, policies (v0.3)
harness.py          older batch keyword-matcher prototype (see below)
tests/              pytest suite
docs/               spec, planning and handover documents
samples/            NOT in git: 10 real sample PDFs, shared separately
```

`harness.py` is a separate, older track. It runs a keyword matcher against
synthetic text (`harness_demo_fixture.json`) and has two known bugs: ties are
broken by knowledge-base order, and dates are grouped as strings. Whether it becomes an offline batch tester or is
retired is still undecided.

### Run the tests

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

Use `python -m pytest`, not bare `pytest`. On Windows the bare command depends on
`PATH`. `requirements-dev.txt` adds `pytest` and `httpx` to `requirements.txt`.

- Tests that read real PDFs are marked `@pytest.mark.samples`. **On a fresh clone they skip, they don't fail.** They run once `samples/` is in place.
- `tests/test_e2e.py` also needs Ollama running with `llama3.1`. It calls the model for real.
- CI (`.github/workflows/tests.yml`) runs `python -m pytest` on Python 3.10 and 3.12 for every PR and every push to `main`. CI has no samples and no Ollama, so those tests skip there.

### Before opening a PR

- Work on a branch (`feature/…`, `fix/…`, `docs/…`), one unit of work per branch. Never commit to `main`.
- `python -m pytest` passes locally.
- Document rules go in `knowledge_base.json`, never hardcoded in Python.
- Update `CHANGELOG.md` in the same PR, and link the GitHub issue the PR closes or opens.

### The failure log must stay de-identified

`failure_log.jsonl` is committed and shared, unlike `samples/`. Every record holds
exactly five fields. `document_id` is the SHA-256 of the file, never a filename
or path. `note` is a reason code, never free text, so no names, account numbers
or figures. Its field names match the planned `failure_log` SQLite table in
`docs/archive/2_ARCHITECTURE.md`. The full rule is in `failure_log.py`'s docstring, and
`tests/test_failure_log.py` fails if a field is added. The file won't exist
until the first verdict is recorded.

### Client documents and samples

- **Client documents never enter git.** `.gitignore` blocks `*.pdf`, `*.docx`, `*.doc` and `*.zip` anywhere in the tree. This is not retroactive: if a client document was ever committed, raise it before pushing.
- **`samples/` is shared outside git** (drive link or direct transfer from Delia), because the samples aren't cleared for a public repo. To add your own, name it `TYPE_Description.pdf` (e.g. `FSG_YourProvider.pdf`), send the file separately, and add its expected result to `docs/sample_documents.labelling.md` through a PR.
- **`docs/` is in git** (since 13 Oct 2026). Change it through a PR like any other file.

### Dependencies

| package | version | used by |
|---|---|---|
| `fastapi` | 0.128.0 | `app.py` |
| `uvicorn` | 0.39.0 | running the app |
| `pypdf` | 6.15.0 | `parser.py` |
| `python-multipart` | 0.0.22 | `app.py` (file upload) |
| `requests` | 2.32.4 | `classifier.py` → Ollama |
| `cryptography` | 50.0.2 | `pypdf`, for encrypted PDFs |

Python 3.10+ is required. `failure_log.py` uses `str | None`, which fails at
import on 3.9 with an error that doesn't mention the version.

Ollama is the current engine. Hosted models (Anthropic, OpenAI) could replace it
later behind the same knowledge-base hints.

### Docs map

| file | what's in it |
|---|---|
| `docs/SYSTEM.md` | the spec: build from this |
| `docs/GROUND_TRUTH.md` | the anchor decisions, including the review-level rule |
| `docs/BUSINESS_CASE.md` | business case |
| `docs/archive/` | the August drafts: product, architecture, handover (history) |
| `docs/advice_classification_reference.md` | the legal basis for each document type and ROA situation |
| `docs/sample_documents.labelling.md` | hand-labelled expected results for `samples/` |
| `docs/EXPERIMENT_LOG.md` | classifier experiments: runs, scores, findings |
| `CHANGELOG.md` | what's done, decided and still open, newest first |
