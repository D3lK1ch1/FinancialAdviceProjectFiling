# Front end (React)

The page the tool shows at `/`: an upload screen, then overview, advice events,
documents needing review, the proposed folder tree, a filing log with undo, and a
document panel with Approve and Reject. The design is from the demo
(`ahaythorpe/advice-document-classifier`, 21 Oct 2026). `docs/ui/` has the
screenshots and `docs/UI_INTEGRATION.md` the reasoning. There is no demo mode and
no built-in data: the page only shows documents you give it.

## Build it and run it

Needs Node 18+.

    cd frontend && npm install && npm run build && cd ..
    python -m uvicorn app:app --port 8000

`npm run build` writes one self-contained file, `dist/index.html`, which FastAPI
serves at http://127.0.0.1:8000/. Drop PDFs on the page. Python reads them
(`POST /api/batch`, the same steps as `/ingest`) and the page shows the results.
Proposals only: nothing is moved, renamed or saved. Approve and Undo change what's
on screen, and a verdict on a document goes to the failure log
(`/review/correction`).

While working on the page, `npm run dev` serves it with live reload and passes
`/api` and `/review` to the backend on port 8000, so keep uvicorn running too.

Automatic batch filing follows `review_policy.one_click`: as documents are read,
everything at or above the line with nothing to check is filed in one batch, logged
in the Filing log, and can be undone (an undone document isn't refiled). 90% is the
floor for real use and a firm can only raise it; while the tool is tested the line can go
to 70%, marked "Testing line".
Below 90% the batch also takes documents held for low confidence alone, never flagged
ones. Nothing is written to disk yet.

## What the page needs: the manifest

Everything on screen comes from what `/api/batch` returns,
`{ "local": { "default": manifest } }` (`manifest.py`). Below is what a manifest
holds and where each part comes from in `/ingest`.

| Manifest field | From `/ingest` today | Gap |
|---|---|---|
| `doc_id` | `document_id` | |
| `source_name` | `filename` | |
| `type`, `type_label` | `classification.doc_type`, `doc_type_name` | |
| `confidence` | `classification.confidence` (the verified figure) | |
| `classification_evidence` | `classification.matched_signals` | join into one line |
| `pages`, `extraction_quality` | `page_count`, `has_selectable_text` | no quality score yet |
| `client`, `client_provenance` | `client_candidates` (none chosen) | #6 / PR #69 |
| `date`, `date_provenance` | `filing.date`, `filing.date_determination` | #48 |
| `needs_review` | `review.needs_review` (reasons in `review.reasons`) | |
| `flags[]`: `id`, `severity`, `message`, `blocks_filing` | `flags[]`: `id`, `severity`, `why` / `asks`, `forces_review` | rename only |
| `destination`: `folder[]`, `filename`, `path`, `rationale` | `filing.client_folder`, `event_folder`, `filename` | step folder #70. The backend deliberately doesn't join a path with a missing part, so the page must show a missing part as missing, never as a real folder. |
| `stages` | `filing.stages` | new names in #70 |
| `event_id`, `events[]` | `filing.event_folder` for SOA and ROA only | grouping other documents, #8 |
| `confidence_threshold` | `review.threshold`, **per type** | the page draws one line; change it to each document's own threshold |
| `knowledge_base_version` | `engine_version` | |
| `batch` counts | none | counted over the batch |

**Correcting a document** is Reject in the document panel: pick what it actually is
(never the type the tool proposed) and why, from `/review/options`. A document with no
proposed type has Reject only.

**Display mode** (#11): the document panel shows the knowledge base's teaching note
for the document's type under "What this document is". "Teaching notes On / Off" in
the title bar shows or hides it and is remembered in the browser. It only hides text:
classification, flags and review never change.

## Still to do

1. **Approve, file and undo for real.**
   - `POST /api/approve {doc_ids, level}` writes through `storage.LocalStorage.put()`,
     never from the classifier (ground rule 3). It appends an entry to a filing log
     and returns the entry.
   - `POST /api/undo {entry_id}` moves the files back and marks the entry undone.
   - The page's `decide` and `undoEntry` in `src/App.jsx` call these instead of
     keeping state in memory.
2. **Package as a desktop app** for non-technical users: one installer, the backend
   and this page in a window, files never leave the computer. The open question
   is how Ollama and the model get installed. Spike this first.
