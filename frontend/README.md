# Front end (React)

The screens from the demo (`ahaythorpe/advice-document-classifier`, 21 Oct 2026):
overview, advice events, document panel, one-click filing, filing log with undo,
folder tree, guided tour. Not yet connected to this repo's Python backend. This
file is the plan for connecting it. `docs/UI_INTEGRATION.md` (PR #72) has the
screenshots and the reasoning.

`sample-data.json` is made-up demo data from the demo repo's pipeline. No real
client data.

## Run it on sample data

Needs Node 18+.

    cd frontend
    npm install
    npm run preview:sample      # writes dist/demo.html; open it in a browser

The page reads one object, `window.DATA`, put in at build time where
`index.html` says `__DATA__`. `npm run dev` won't work until step 2 below
replaces that with a fetch.

## Run it with the Python backend (real PDFs)

    cd frontend && npm install && npm run build && cd ..
    python -m uvicorn app:app --port 8000

Open http://localhost:8000/app/ and choose PDFs. Python reads them
(`POST /api/batch`, the same steps as `/ingest`) and the page shows the results.
Proposals only: nothing is moved, renamed or saved. Approve and Undo only change
what's on screen. Each document takes a minute or more, because every one goes
through the model. The old page is still at http://localhost:8000/.

## What the page needs: the manifest

Everything on screen comes from one object per filing scheme:
`{ dataset: { scheme_id: manifest } }`. Below is what a manifest holds and where
each part would come from in `/ingest` today.

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

**Missing from the React page that the current `static/index.html` has.** These
must carry over before the React page replaces it:
- **Edit:** correcting the type, with a reason code from `/review/options`. The React
  page has Approve and Reject only.
- **Recording verdicts to the failure log** (`/review/correction`), with the engine stamp.
- **Display mode** (teach or don't, #11).

## Connecting it, step by step

1. **Backend: a batch endpoint that returns a manifest.** For example
   `POST /api/batch` with a folder, running the `/ingest` steps over each file and
   grouping them (#8). Until grouping lands, every document sits under "Outside
   any advice event", which is honest. Rules stay in the knowledge base.
2. **Page: fetch instead of `window.DATA`.** One place changes: `DATASETS` in
   `src/model.js`. Keep the `__DATA__` build for the sample demo.
3. **Serve the built page from FastAPI** at `/`, the way `static/index.html` is
   served today. One program on one port, nothing else to install for the
   person using it.
4. **Approve, file and undo for real.**
   - `POST /api/approve {doc_ids, level}` writes through `storage.LocalStorage.put()`,
     never from the classifier (ground rule 3). It appends an entry to a filing log
     and returns the entry.
   - `POST /api/undo {entry_id}` moves the files back and marks the entry undone.
   - The page's `approveBatch`, `decide` and `undoEntry` in `src/App.jsx` call these
     instead of keeping state in memory.
5. **Filing schemes from the knowledge base**, not `profiles/*.json` copied by hand
   (#70, PR #28, #71 later).
6. **Package as a desktop app** for non-technical users: one installer, the backend
   and this page in a window, files never leave the computer. The open question
   is how Ollama and the model get installed. Spike this first.
