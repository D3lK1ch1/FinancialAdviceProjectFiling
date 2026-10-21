# Business Case — AI Document Classification & Filing for Australian Advice Firms

**Status:** Working draft (v0.2, refreshed 21 Oct 2026) · Owner: Bella · Audience: internal working doc
**Note on data:** Market figures below are from the research scan; several (esp. Xplan pricing) are **not publicly verifiable** — treat as indicative and validate before any external use. See Caveats.

---

## Where it stands (21 Oct 2026)

**What the prototype does today**
- Reads a client's PDFs on the firm's own computer and works out each one's type, client
  and advice event. A local model is used, so no client file leaves the computer.
- Proposes where to file: client, then advice event, then planning step
  (`1 Goals and situation`, `2 Advice`, `3 Implementation`), named
  `Surname_First name_YYYY-MM-DD Type.pdf`.
- Holds anything it isn't at least 90% sure of, or that has a compliance point, for a
  person, with the reason. The confident ones are approved together in one click.
- Every filing is logged and can be undone (on screen today; real file moves are next).

**What it doesn't do yet:** move real files, group every document with its advice, or
read the provider forms that implement advice. Accuracy on real documents isn't proven.
It isn't ready to show outside the team.

**Evidence still needed before this case can be relied on**
1. **The problem, from practices.** Interview 5 to 10 small practices: hours spent
   filing each week, what goes wrong, what a misfiled record costs at a review.
2. **Accuracy.** An agreed target (for example, 95% filed correctly on a real
   practice's files, nothing wrong filed without a flag), measured on enough documents.
3. **A pilot practice** willing to test it on its own computer.
4. **Privacy and legal advice** on a tool reading client files, even locally, and on the
   AFSL boundary (section 11).
5. **Pricing reality.** What target firms pay now for Xplan, AdviserLogic, Practifi or
   Virtual Cabinet (the figures below are partly unverified).
6. **An agreement between Bella and Delia** on ownership and decisions.

## 1. The opportunity in one line

No major Australian advice platform does **true AI document-type classification**. Incumbents store; nobody identifies. A cheap, advice-native classifier that sits on top of existing systems is genuine white-space.

## 2. The gap

Across Xplan, AdviserLogic, Midwinter, Worksorted, Practifi and myprosperity, "document handling" = manual filing + rules-based naming + a client portal. None reads a document and determines "this is an SOA / ROA / FSG / PDS / fact find." The only players doing real AI classification are:
- **Accounting-market tools** (FYI launched "FYI AI" auto-filing in 2025; The Drive AI; Docupile) — none understands Australian advice document types or Corporations Act record-keeping.
- **AI SOA *drafting* tools** (Marloo, Flynance, Zatersio, BackPro, Nod) — they *generate* documents; they don't classify and file what a firm already holds.

That is the wedge: **advice-native classification of documents a firm already has.**

## 3. Why now (tailwinds)

- **Incumbent fatigue:** Xplan ~60% share / ~38k users, but described as expensive, complex, clunky; weak document search (can't search file-note subject lines); disliked "threads"; auto-renewing 12-month lock-in contracts (Jul 2024) angered advisers.
- **Shrinking, cost-squeezed market:** advisers ~28,000 (2018) → ~15,500 (Oct 2025), across ~6,000 mostly micro-practices (avg 2.5 advisers). Median ongoing fee +18% in 2025 to $4,668 (+67% over 5 years vs ~20.5% inflation). Cost-to-serve pressure is acute.
- **AI adoption rising, classification still unsolved:** 61% of advisers use AI (Investment Trends 2025), mostly drafting/notes; document classification/filing is not yet a category in the advice vertical.
- **Regulatory migration moment:** DBFO Tranche 2 replaces SOAs with Client Advice Records (CARs). Record-keeping stays heavy; firms must rework templates/processes — a natural moment to sell a re-classify-and-re-file service.

## 4. Target customer

Sole practitioners and micro-practices (~6,000 firms) — most squeezed on cost, least served by enterprise tooling, fastest to decide. Land here, expand to small licensees.

## 5. Positioning

- **Overlay, not replacement.** Ride alongside Xplan/AdviserLogic/Midwinter via file tree / API. Switching core systems is too painful ("necessary evil") — don't ask them to.
- **Advice-native, not generic.** Understands SOA vs ROA (three situations) vs FSG vs PDS and Corporations Act record-keeping — where accounting DMS tools can't follow.
- **Cheap and no lock-in.** Deliberate contrast to Iress's pricing and contracts.
- **Australian data sovereignty.** No offshore handling of client data/TFNs — table-stakes.

## 6. Competitive landscape (summary)

| Product | Market | Doc handling | Classification | Price signal |
|---|---|---|---|---|
| **Xplan (Iress)** | Advice (incumbent) | Storage, threads, weak search | Manual | High, opaque (~$7k/adviser p.a., *unverified*) |
| **AdviserLogic (Morningstar)** | Advice | Generation + storage | Rules-based | Not public; ~45-day onboarding |
| **Midwinter AdviceOS (Bravura)** | Advice + super | SOA/ROA gen, portal | Rules-based | Modular, not public |
| **Plutosoft** | Advice | End-to-end CRM | Rules-based | Positions as cheaper than Xplan |
| **Worksorted** | Advice | Doc vault, anti-"threads" | Rules-based | Not public |
| **Practifi** | Larger advice/RIA | Salesforce-based | Rules-based | On application (upmarket) |
| **myprosperity** | Advice + accounting | Client portal storage | None (portal) | — |
| **FYI** | **Accounting** | Strong auto-filing/naming | **AI (2025), non-advice** | $30–70/user/mo, min 5, needs M365 |
| **SuiteFiles** | Accounting/prof svcs | DMS + email filing | Rules-based | ~$29–70/user effective |

**Read:** cheaper/simpler tools are accounting-first or CRM-first. The advice-document classification slot is empty.

## 7. Pricing strategy

- Enter **well below Xplan**: target ~**$20–40/user/month** for the classification/filing layer, **or usage-based (per-document)** to capture sole traders and micro-practices.
- **No lock-in**, onboarding in days (undercut FYI/SuiteFiles on speed + total cost; they need M365 + migration consultants).
- Benchmarks: FYI $30–70/user/mo; SuiteFiles ~$29–70/user; OPEX advice-doc tooling $495–995/mo; Flynance usage-based ($30/SOA).

## 8. Go-to-market (staged)

- **Stage 1 (0–6mo):** the wedge — ingest existing pile, auto-identify type, apply convention, route to client → advice event → planning step, one-click approval of the confident ones, review queue for the rest, log with undo. Overlay via file tree/API. Australian data handling.
- **Stage 2 (6–12mo):** compliance-grade record management — version tracking, **missing-record detection** (flag clients with no current FSG/fact find/FDS), CAR-ready record-keeping. Sell the DBFO migration: bulk re-classify back-catalogues.

## 9. What would make advisers switch (win conditions)
1. No manual filing for routine documents: one click approves the confident ones, and a person only handles what the tool holds (a person always approves; nothing files automatically).
2. Sub-second, content-based search by **type** and **subject** — directly targets Xplan's admitted subject-search failure.
3. No core-system rip-and-replace.
4. Transparent, low, no-lock-in pricing.

## 10. Threats & responses
- **Iress ships AI auto-filing** → wedge narrows; accelerate into Stage 2 (record-completeness, CAR workflows) where incumbents are weakest; lean on price + integration neutrality.
- **FYI extends into advice** with Corporations Act/CAR awareness → same response; emphasise advice-native depth (ROA three situations, CAR seam).
- **Drafting tools drift into classification** → window is finite; move to own the niche now.

## 11. Regulatory boundary
Tool classifies and files; it does **not** provide financial advice. AFSL boundary must be validated with a lawyer **before commercial sale**. Nothing here is legal advice.

## 12. Caveats
- **Xplan pricing not publicly verifiable** — the ~$7k/adviser figure is a single consultant's flagged estimate.
- Some pain-point commentary comes from Iress-owned (Advisely) or competitor (Worksorted, Plutosoft) sources — weigh accordingly.
- G2's Xplan sample is tiny; the "necessary evil" narrative rests on Money Management's named-adviser interviews.
- DBFO Tranche 2 is **draft** legislation; SOAs won't vanish imminently; record-keeping persists under CARs.
- Vendor adoption stats (Netwealth "Stars", Investment Trends) skew to digitally mature firms and may overstate baseline adoption among the micro-practices you're targeting.

## 13. Sources (key)
- Money Management — "Is Xplan a 'necessary evil'…" (Feb 2024)
- Professional Planner — "Iress infuriates advisers…" (Jul 2024); "DBFO Tranche 2 arrives, swapping SOAs for CARs" (Mar 2025)
- Iress Advisely forum — file-note search limitations
- Lexology — "DBFO Tranche 2: two steps forward, one step back"
- Netwealth 2025 AdviceTech; Investment Trends 2025 Adviser Technology Needs Report; Adviser Ratings 2025 Landscape Report
- Vendor sites: FYI, SuiteFiles, Worksorted, AdviserLogic, Midwinter, Plutosoft, Practifi, myprosperity
