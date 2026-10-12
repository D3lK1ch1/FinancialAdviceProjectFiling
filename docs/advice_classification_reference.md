# Advice Classification Reference

**What this is:** the domain model behind the classifier — how document types map to advice
types, advice-process stages, the safe harbour compliance steps, and legal bases. This is the
authoritative research note that underpins both `knowledge_base.json` and the teaching content.

**Audience:** the domain collaborator (domain owner) and the developer/data scientist.
**Last updated:** 2026-08-20.
**Status:** current-regime (pre-DBFO-Tranche-2). See §5 for the reform seam.

---

## 1. The core idea

The whole system hangs on one principle: **the type of advice determines which document is
legally required.** Everything else is downstream of that.

When an adviser gives *personal advice* (advice that takes the client's specific situation into
account), the law imposes the **best interests duty** — s961B(1) of the Corporations Act 2001.
That duty is broad and hard to prove you've met. So s961B(2) provides a **safe harbour**: seven
steps which, if followed and documented, are deemed to satisfy the duty.

The SOA (or ROA) is the document that *evidences* the safe harbour. Every other document either
feeds into it or flows out of it. Find the SOA and you've found the centre of an advice event.

Two honest caveats to hold throughout:
- The safe harbour is a **process defence, not a quality guarantee**. Following the seven steps
  doesn't automatically mean the advice was genuinely in the client's best interest (advice
  *quality* is a separate duty, s961G). It's the most common compliance route, not the only one.
- This is the **current regime**. DBFO reform is reshaping it slowly — see §5.

---

## 2. The advice process, mapped to compliance steps and documents

Six process stages, the safe harbour step each corresponds to, and the document produced.

| Process stage | Safe harbour step (s961B(2)) | Document produced | Legal basis |
|---|---|---|---|
| Initial consultation | Pre-step — give FSG, agree scope | FSG (+ engagement letter) | s941A |
| Discovery (know your client) | Steps 1–2: identify goals; find gaps | Fact find, risk profile | evidences s961B(2)(a)–(b) |
| Research & strategy | Steps 3–6: competence, investigate, base advice on it, prioritise client | (internal file notes) | s961B(2)(c)–(f) |
| Advice delivery | Step 7: any other step in the client's best interests | **SOA or ROA** | s946A |
| Implementation | Post-advice — client authorises, execute | ATP, applications, insurance docs | follows SOA/ROA |
| Ongoing review | Post-advice — annual service, monitor | FDS (+ new ROA) | s962H |

### The seven safe harbour steps, in plain words
1. **Identify the client's circumstances** — objectives, financial situation, needs (ideally in
   their own words).
2. **Identify gaps** — where the information is incomplete or inaccurate, make reasonable inquiries.
3. **Assess your own competence** — confirm you have the expertise for what they need.
4. **Investigate products/strategies** — reasonable research into what might meet their needs.
5. **Base the advice on that investigation** — recommendations flow from the research.
6. **Prioritise the client's interests** — ahead of your own or any related party's.
7. **Any other step** reasonably regarded as being in the client's best interests (catch-all).

Steps 1–2 are evidenced at **discovery** (fact find, risk profile). Steps 3–6 are the behind-the-
scenes **research & strategy** work. Step 7 and the write-up land at **advice delivery** — which
is where the SOA/ROA is produced. An adviser who can demonstrate each step is *deemed* to have
acted in the client's best interests; the SOA is that demonstration on paper.

---

## 3. Advice-type decision tree (runs first, upstream of the process)

This decides which document the engagement must produce. It runs at the START.

```
Client interaction — does it consider the client's personal situation?
│
├─ No  → GENERAL ADVICE
│        → General advice warning (s949A). No SOA. Does NOT trigger safe harbour.
│
└─ Yes → PERSONAL ADVICE  (triggers best-interests duty, s961B; full process applies)
         │
         ├─ New advice, or material change → SOA (s946A)
         │     ├─ Comprehensive → full SOA
         │     └─ Scaled / limited → short SOA (RG 90 · INFO 267)
         │
         └─ Existing client, no material change → ROA
               └─ Four legislative bases — confirm which (see §4)
```

Key fork: **general advice stops at a warning; personal advice pulls the engagement through the
full six-stage process and the seven safe harbour steps.** A document only makes sense in light of
what kind of advice produced it — which is exactly what the classifier exploits.

---

## 4. The four ROA bases (why an ROA is a "confirm which kind" flag, not an error)

An ROA legitimately has four distinct legislative bases. Encountering one is therefore a
**medium-severity "confirm which basis" flag**, not a high-severity error.

| Basis | Legislative reference | Plain description |
|---|---|---|
| Further advice | reg 7.7.10AE | Existing client, no material change since last SOA |
| Hold / no-action | s946B(7) | "No change" recommendation |
| Small investment | s946AA | Below the value threshold |
| No buy/sell | reg 7.7.10AAA | Recommendation not to transact |

**Sample-set note:** ASIC's INFO 266 examples cover three of these four — att 1 = further advice,
att 2 = no-change (NOT "further advice" — the old filename was wrong), att 3 = stockbroker/small-
investment flavour. The fourth (no buy/sell) is a known gap; don't source it artificially — let a
low-confidence flag catch it if it appears in real data.

---

## 5. DBFO reform — the forward seam

**DBFO = Delivering Better Financial Outcomes**, a government reform package aiming to make advice
cheaper and simpler by cutting red tape. It comes in tranches.

- **Tranche 1** — law since 9 July 2024. Fee-consent mechanics, FSG-on-website changes. Did NOT
  touch the SOA or the advice process.
- **Tranche 2** — NOT yet law (as of late 2025; delayed, now bundled with Tranche 3 to go to
  Parliament together, no firm timeline). Headline: replace the SOA with a **Client Advice Record
  (CAR)**.

What matters for the classifier:
- The CAR keeps the **same triggers** as the SOA, and ROAs survive alongside it. So the reform is
  a **relabel, not a rebuild**.
- A CAR won't have to be in writing (could be audio or email for simple advice) — so eventually
  the system may need to classify non-PDF advice records. Not now, but it's why the seam exists.
- The **safe harbour is NOT being removed** (that reform was deferred out of Tranche 2). The seven
  steps in §2 remain current law for the foreseeable future.

**Honest framing:** the SOA→CAR transition is a real but *soft and slow* tailwind. Commentators
widely call Tranche 2 a missed opportunity unlikely to make CARs much shorter than SOAs. Don't
build the pitch on "DBFO forces migration." The firmer wedge is the operational pain firms have
*today* — messy document piles regardless of reform. DBFO is an accelerant to mention, not the
foundation.

**The `advice_record_role` field is the seam.** Today: SOA→`SOA`, ROA→`ROA`. When Tranche 2 lands,
the SOA row's role flips to `CAR` and nothing else moves.

---

## 6. Master mapping table (the classification engine)

Document type is the spine. The classifier identifies `doc_type` from content, looks up the row,
and that row populates advice type, process stage, compliance step, and flag behaviour.

| doc_type | Advice type implied | Process stage | Safe harbour step | Legal basis | advice_record_role | Flag behaviour |
|---|---|---|---|---|---|---|
| FSG | Any advice relationship | Initial consultation | Pre-step | s941A | — | None expected |
| Fact find | Personal advice (input) | Discovery | Steps 1–2 | s961B(2)(a)–(b) | — | None; absence upstream of SOA = flag |
| Risk profile | Personal advice (input) | Discovery | Steps 1–2 | s961B(2)(b) | — | None; pairs with fact find |
| SOA | New personal advice | Advice delivery | Step 7 | s946A | `SOA` (→`CAR`) | Sub-type: comprehensive vs scaled/limited |
| ROA | Further personal advice | Advice delivery / ongoing | Step 7 | reg 7.7.10AE · s946B(7) · s946AA · reg 7.7.10AAA | `ROA` | **Medium: confirm which of 4 bases** |
| ATP | Implementation authority | Implementation | Post-advice | follows SOA/ROA | — | None; should follow an SOA/ROA |
| Application / insurance | Product implementation | Implementation | Post-advice | s1012 | — | None; cluster with advice event |
| FDS | Ongoing service | Ongoing review | Post-advice (annual) | s962H | — | None; recurring per client/year |
| PDS | General (product info) | Any (reference) | Not a safe-harbour doc | s1013 | — | None; product-issuer doc |
| Engagement letter | Scope-setting | Initial consultation | Pre-step | contractual / scope | — | None; precedes discovery |

### The three load-bearing rows
- **SOA/ROA** — the only documents that *are* safe-harbour evidence (step 7). Everything else
  feeds in or flows out. This is why clustering works: the SOA is the centre of an advice event.
- **ROA** — four bases → the engine can't stop at "ROA, done"; it raises the confirm-which-basis
  flag. This is what makes it domain-aware rather than a dumb type-detector.
- **advice_record_role** — the DBFO seam, live in only the SOA and ROA rows.

### Two limits on the table (for the developer)
- The safe-harbour-step column is a mapping for **teaching and confidence**, not a legal
  determination. A document sitting at a stage doesn't prove the step was satisfied — it tells the
  engine where the document belongs.
- This is the **current regime**. When Tranche 2 changes the SOA rules, the SOA and ROA rows need
  re-checking against final drafting — which is why the AFSL-boundary legal sign-off sits ahead of
  any *compliance* use (as opposed to filing).

---

## 7. Sources

- Best interests duty & safe harbour — Corporations Act 2001, s961B(1) and (2) (austlii.edu.au)
- ASIC Regulatory Guide 175 — Licensing: Financial product advisers
- The seven safe harbour steps — as summarised in ASIC guidance and industry compliance material
- ROA bases — Corporations Regulations 2001 (reg 7.7.10AE, 7.7.10AAA) and Corporations Act
  (s946B(7), s946AA); ASIC INFO 266
- Example advice documents — ASIC RG 90 (SOA), INFO 267 (limited-advice SOA), INFO 266 (ROAs)
- DBFO reform — Treasury DBFO package; ASIC DBFO page; Treasury Laws Amendment (DBFO) Act 2024
  (Tranche 1); Tranche 2 exposure draft (Mar 2025); industry commentary (Hamilton Locke, KWM,
  Professional Planner, IFA) on status and scope

**Note on currency:** DBFO is live, moving legislation. Verify the Tranche 2 Bill's current status
before using any DBFO claim in a pitch or compliance context.
