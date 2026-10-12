# Technical Architecture — AI Document Classification & Filing

**Status:** Working draft (v0.1) · Owner: domain collaborator · Audience: internal + dev/data scientist
**Companion to:** `1_PRD.md`, `SYSTEM.md`, `CLAUDE.md`

---

## 1. Architecture at a glance

```
                ┌─────────────────────────────────────────────┐
                │                 UI layer                    │
                │  React + Vite + Tailwind                    │
                │  ┌─────────────┐   ┌──────────────────────┐ │
                │  │ Review queue │   │ New-to-industry /    │ │
                │  │ (approve/fix)│   │ Experienced modes    │ │
                │  └─────────────┘   └──────────────────────┘ │
                └───────────────────────┬─────────────────────┘
                                        │ REST (JSON)
                ┌───────────────────────▼─────────────────────┐
                │              API layer (FastAPI)             │
                │  /ingest  /classify  /file  /review  /flags  │
                └───┬───────────┬────────────┬────────────┬────┘
                    │           │            │            │
        ┌───────────▼──┐ ┌──────▼──────┐ ┌───▼─────────┐ ┌▼──────────────┐
        │  Parser       │ │ Classifier  │ │ Filing      │ │ Flagging      │
        │ pypdf /       │ │ LLM → JSON  │ │ engine      │ │ engine        │
        │ pdfplumber    │ │ + KB hints  │ │ client→event│ │ 11 rules      │
        └───────┬───────┘ └──────┬──────┘ └──────┬──────┘ └───────┬───────┘
                │                │               │                │
                └────────────────┴───────┬───────┴────────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │  Shared knowledge layer          │
                        │  knowledge_base.json (v0.3)      │
                        │  — powers classifier hints AND   │
                        │    teaching content              │
                        └────────────────┬─────────────────┘
                                         │
                        ┌────────────────▼─────────────────┐
                        │  Storage: SQLite                  │
                        │  documents, classifications,      │
                        │  flags, failure_log, clients,     │
                        │  advice_events                    │
                        └───────────────────────────────────┘
```

## 2. Stack (locked)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | React, Vite, Tailwind | Two display modes over one engine |
| Backend | Python, FastAPI | JSON REST |
| Parsing | pypdf, pdfplumber | OCR fallback deferred |
| Classifier | LLM returning JSON (Phase 1) | KB supplies hints/signals |
| Storage | SQLite | Single-practice scale; defer multi-tenant |
| Dev | Claude Code | `CLAUDE.md` handover brief |
| Knowledge | `knowledge_base.json` | Single source powering classifier + teaching |

## 3. Pipeline (request path)

1. **Ingest** — folder or single file → parser extracts text + metadata → raw record persisted.
2. **Classify** — text + KB signals → LLM → JSON `{doc_type, confidence, advice_record_role, matched_signals, flags[]}`.
3. **Flag** — flagging engine applies the 11 rules (e.g. ROA four-bases → "confirm which kind", medium).
4. **File (propose)** — filing engine maps to `client → advice_event` path, applies naming convention, or routes to `_Needs review` if confidence below threshold.
5. **Review** — human approves / corrects; approval commits the file move, correction writes to `failure_log`.

## 4. Data model (SQLite, indicative)

```sql
clients(id, name, identifiers, created_at)
advice_events(id, client_id, event_type, event_date, label)

documents(
  id, source_path, ingested_at, raw_text_ref,
  parsed_ok BOOLEAN
)

classifications(
  id, document_id, doc_type, confidence REAL,
  advice_record_role,        -- absorbs SOA→CAR relabelling
  matched_signals JSON,      -- why this label (explainability)
  suggested_path TEXT,
  status,                    -- proposed | approved | corrected
  model_version, created_at
)

flags(
  id, document_id, rule_id, severity,   -- e.g. 'roa_basis' / medium
  message, resolved BOOLEAN
)

failure_log(
  id, document_id, predicted_type, correct_type,
  note, logged_at            -- feeds tuning + metrics
)
```

## 5. Classifier design (Phase 1)

- **LLM returns strict JSON** — no prose. System prompt specifies schema, forbids preamble/markdown fences; response parsed safely (strip fences, try/catch).
- **KB-driven hints:** `knowledge_base.json` supplies per-type signals (headings, phrases, disclosures, legislative references) fed into the prompt so classification is grounded, not guessed.
- **Confidence + threshold:** below threshold → `_Needs review`. Threshold tunable per type (some types are higher-stakes).
- **Hard-case handling:**
  - **SOA vs ROA** — both advice records; look for issue-scope, disclosure set, "record of advice" markers. ROA's **four legislative bases** must be distinguished, not collapsed (prior error: treating as one changed flag severity from high to medium "confirm which kind").
  - **FSG vs PDS** — provider-disclosure vs product-disclosure signals.
  - **Fact find vs risk profile** — data-collection vs risk-tolerance instrument.
- **Explainability:** persist `matched_signals` so the review UI shows *why*.

## 6. Filing engine

- Two-axis nested: `/<Client>/<Advice Event>/...` + `/<Client>/_ClientLevel/` for FSGs etc. + top-level `_Needs review/`.
- Client + event resolution: match against `clients`/`advice_events`; unresolved client or event → review.
- Naming convention configurable per practice; applied on output only (never mutate originals in place — copy/route with audit trail).

## 7. Flagging engine

- Rules loaded from KB (11 rules). Each: `{rule_id, applies_when, severity, message}`.
- Deterministic layer on top of the probabilistic classifier — cheap, auditable, testable via `harness.py`.

## 8. Forward-compatibility (DBFO / SOA→CAR)

- `advice_record_role` is the seam. When CARs land, relabel via KB + role flag; **no schema rebuild**. SOA and CAR are both "advice records" differing in role/label.
- Keep record-keeping obligations modelled separately from the advice-record document itself (mirrors the CAR "records to demonstrate compliance, separate from CARs" requirement).

## 9. Testing & quality

- `harness.py` — keyword/signal test harness over `sample_documents.json`.
- **Maintained failure log** — every misclassification recorded; drives tuning and the success metrics in the PRD.
- Build in **small, testable steps**; deterministic flagging engine is unit-testable independent of the LLM.

## 10. Deployment direction (open)

- **Desktop app** the leading candidate; unresolved: prototype vs working app, browser-based vs installed.
- Overlay-first: operate on a local file tree / export folder before attempting API integration with Xplan/AdviserLogic/Midwinter.
- **Data sovereignty:** keep processing in-country; if any LLM call leaves the machine, ensure Australian-region handling and no TFN/client-data retention offshore.
- Cloud/multi-tenant deferred until pilot complete.

## 11. Security & compliance notes
- No client data or TFNs processed offshore.
- Originals immutable; all moves logged (audit trail).
- Human approval gates every file action.
- AFSL boundary: tool classifies and files; it does not give advice. Legal sign-off required before commercial sale — this doc is not legal advice.
