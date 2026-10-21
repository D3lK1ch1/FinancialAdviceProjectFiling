# PRD — AI Document Classification & Filing for Australian Financial Advice Firms

**Status:** Working draft (v0.1) · Owner: domain collaborator · Audience: internal working doc
**Related artefacts:** `knowledge_base.json` (v0.3), `harness.py`, `sample_documents.json`, `SYSTEM.md`, `CLAUDE.md`

---

## 1. Problem

Australian advice firms hold large volumes of regulated documents (SOAs, ROAs, FSGs, PDSs, fact finds, risk profiles, insurance, tax, ATPs, declarations, nominations, supporting docs). Today these are filed **manually** into incumbent systems (Xplan, AdviserLogic, Midwinter) using hand-applied naming conventions and folder/cabinet taxonomies. Incumbents do **storage**, not **identification** — none reads a document and determines its type, applies the firm's convention, routes it to the right client/event, tracks versions, or flags missing records.

Pain is concentrated at the incumbent: Xplan (~60% share, ~38k users) is widely described as expensive, complex, and clunky, with weak document search (can't search file-note subject lines) and disliked workflow "threads." Adviser numbers have roughly halved since 2018 (~15,500 in Oct 2025), cost-to-serve is rising, and DBFO Tranche 2 (SOA→CAR) is forcing every firm to rethink record-keeping — a migration moment.

## 2. Goal & non-goals

**Goal:** A cheap, simple, advice-native layer that ingests a firm's documents, **identifies the document type**, applies the firm's naming convention, routes to the correct client → advice-event folder, and surfaces low-confidence items for human review.

**Non-goals (v1):**
- Not replacing the core CRM/planning system — sit *on top of* it.
- Not auto-filing without human approval — **human-in-the-loop is non-negotiable**.
- Not drafting/generating advice documents (that's a separate, crowded market).
- No cloud-scale infrastructure until a pilot proves value.
- No legal/AFSL advice baked in — boundaries validated externally before commercial sale.

## 3. Users & modes

Two display modes over one classification engine:
- **New-to-industry mode** — teaches what each document is, why it exists, where it sits in the advice process.
- **Experienced mode** — identification + version tracking only, no educational content.

Primary early customers: sole practitioners and micro-practices (~6,000 firms, avg 2.5 advisers) most squeezed on cost and least served by enterprise tooling.

## 4. Core user stories

1. As an adviser, I drop a folder of mixed PDFs and the system tells me what each one is and where it should go, so I stop filing by hand.
2. As a reviewer, I see a `_Needs review` queue of low-confidence placements so nothing files silently.
3. As a paraplanner, I can tell an SOA from an ROA from an FSG by content, not filename, so misfiled docs stop slipping through.
4. As a compliance-minded principal, I can see which clients are **missing** a current FSG / fact find / FDS.
5. As a new staff member, I can learn the document landscape while I work (teaching mode).

## 5. Functional requirements

### 5.1 Ingestion
- Accept PDF (native + scanned), and common office formats.
- Parse text via `pypdf` / `pdfplumber`; OCR fallback for scans (later phase).
- Batch ingest from a local folder; single-file ingest for spot checks.

### 5.2 Classification
- Return **document type** from the nine+ types in `knowledge_base.json`, with a confidence score.
- Distinguish the hard cases: **SOA vs ROA** (and the three situations that permit an ROA), FSG vs PDS, fact find vs risk profile.
- Emit structured JSON: `{doc_type, confidence, advice_record_role, matched_signals, suggested_path, flags[]}`.
- `advice_record_role` flag absorbs the DBFO SOA→CAR transition via **relabelling, not rebuilding**.

### 5.3 Edge-case flagging
- Apply the flagging rules from the knowledge base, `edge_case_flags` (12 as of 13 Oct 2026; e.g. `roa_basis_unconfirmed` — "ROA: confirm which of three situations", severity medium).
- Never silently resolve ambiguity — flag and route to review.

### 5.4 Filing model
- Nested two-axis: **client (outer) → advice event (inner)**.
- Dedicated folder for client-level docs (e.g. FSGs) that don't belong to one event.
- `_Needs review` queue for low-confidence placements.
- Apply the firm's configurable naming convention on output.

### 5.5 Human-in-the-loop review
- System **proposes**; human **approves**. No auto-file in v1.
- Review UI shows: proposed type, confidence, the signals that drove it, suggested path, any flags.
- One-click accept / correct / reflag. Corrections feed the failure log.

### 5.6 Missing-record detection (Phase 2)
- Per client, check for presence of expected current records (FSG, fact find, FDS) and flag gaps.

## 6. Non-functional requirements
- **Data sovereignty:** Australian processing; no offshore handling of client data/TFNs. Table-stakes in this market.
- **Speed:** content-based search returns in sub-second on a typical practice corpus.
- **No lock-in:** deliberately contrast Iress's auto-renewing 12-month contracts.
- **Auditability:** every classification + filing decision logged with the signals behind it.
- **Explainability:** show *why* a doc was classified as X (matched signals), not just the label.

## 7. Success metrics
- % of documents classified correctly at first pass (target: high on the nine core types; measure per type).
- % requiring manual review (should fall as the model tunes).
- Time-to-file per document vs manual baseline.
- Missing-record flags surfaced that the firm didn't know about.
- Failure-log trend (errors caught and fixed over time).

## 8. Phasing
- **Phase 1 (0–6mo):** ingestion → classification → suggested filing → review queue. Overlay only. LLM-based classifier returning JSON.
- **Phase 2 (6–12mo):** version tracking, missing-record detection, CAR-ready record-keeping, AI summary per advice event.
- **Deferred:** cloud infra, scaling, multi-tenant — until pilot complete.

## 9. Open questions
- Desktop app direction: clickable prototype vs working app; browser-based vs installed. **(Unresolved — decide before build.)**
- Integration path: file-system overlay first, or API integration with Xplan/AdviserLogic/Midwinter?
- Pricing model: per-user (~$20–40/user/mo) vs usage-based (per-document) to reach sole traders.
- AFSL boundary: what the tool can claim/do before it strays into regulated advice territory — legal sign-off required.

## 10. Risks
- **Incumbent catch-up:** if Iress ships credible AI auto-filing, or FYI extends FYI AI into advice with Corporations Act/CAR awareness, the pure-classification wedge narrows → accelerate into Phase 2 (record-completeness, CAR workflows) where incumbents are weakest.
- **AI drafting tools drift into filing:** the window to own advice-native classification is finite.
- **Data verifiability:** Xplan pricing and some adoption stats are not publicly confirmable — validate before pricing/positioning decisions.
