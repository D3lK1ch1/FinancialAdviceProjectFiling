# Advice Classification Reference

**What this is:** the domain model behind the classifier — how document types map to advice
types, advice-process stages, the safe harbour compliance steps, and legal bases. This is the
authoritative research note that underpins both `knowledge_base.json` and the teaching content.

**Audience:** the domain collaborator (domain owner) and the developer/data scientist.
**Last updated:** 2026-09-29. Aligned with the live `knowledge_base.json` in the
`FinancialAdviceProjectFiling` repo (issue #41). Where this note and the knowledge base disagree,
the knowledge base wins.
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

> **Note (21 Oct 2026):** this table is the compliance view. For filing, the tool uses
> the six-step financial planning process (define the relationship, identify goals,
> assess the situation, develop the plan, implement, review) in `advice_process_stages`,
> with folders for the practical steps only (#70). Discovery here is steps 2 and 3
> there; advice delivery is step 4; implementation is step 5.

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
               └─ Three situations — confirm which (see §4)
```

Key fork: **general advice stops at a warning; personal advice pulls the engagement through the
full six-stage process and the seven safe harbour steps.** A document only makes sense in light of
what kind of advice produced it — which is exactly what the classifier exploits.

---

## 4. The three ROA situations (why an ROA is a "confirm which kind" flag, not an error)

> **Corrected 17 Sep 2026 — this section previously said four.** See issue #33. The old list
> carried "Hold / no-action (s946B(7))" and "No buy/sell (reg 7.7.10AAA)" as separate bases.
> They are **one situation**: the Act's s946B(7) *is* the no-buy/sell provision, and
> reg 7.7.10AAA substitutes a notional version of it and sets its content requirements — the
> regulation's own title is "Record of advice without a recommendation to purchase or sell".
> ASIC's FAQ lists three. The old list counted one situation twice.

An ROA is permitted in three situations. Encountering one is therefore a **medium-severity
"confirm which kind" flag**, not a high-severity error.

| Situation | Legislative reference | Plain description |
|---|---|---|
| Further advice | notional s946B(2)–(3), via reg 7.7.10AE | Existing SOA client, circumstances and basis not significantly different |
| No buy or sell product advice | notional s946B(7)–(8), via reg 7.7.10AAA | No recommendation to acquire or dispose of a specific product, and no recommended change to strategy or contribution level |
| Small investment advice | s946AA + reg 7.7.09A | Financial investments not exceeding $15,000 |

**"Hold" is not a basis — it is what the advice recommends.** Which situation permits the ROA,
and what the advice says, are two different things, and collapsing them is what made the old
list wrong. An ROA can be *further advice* whose *recommendation* is no change.

**Situation 2 has a second limb that is easy to miss:** the provider and certain associates must
receive **no remuneration or benefit** in relation to the advice, and conflicts must be disclosed.
For a client on an ongoing fee arrangement that will usually fail — which is why an annual-review
"no change" recommendation is normally documented as *further advice*. Content alone never
establishes this basis.

**Sample-set note (corrected).** ASIC's INFO 266 examples cover **one situation, three times**.
All three attachments cite notional s946B(2) and reg 7.7.10AE:

- **att 1** — "Retain existing products and increase insurance". Further advice.
- **att 2** — titled "No change advice", and it relies on **further advice**, because the client
  had an SOA from 2018. An earlier version of this note said it was NOT further advice. That was
  wrong.
- **att 3** — "Stockbroker". Contains neither "s946AA" nor "small investment"; cites reg 7.7.10AE.

So **two of the three situations have no real example anywhere in the set**. Don't source them
artificially — a mock is written by whoever wrote the rules that read it, so it matches by
construction and tests nothing. Let a low-confidence flag catch them if they appear in real data.

**One thing unresolved:** ASIC's 2021 media release describes INFO 266 as explaining "four
exemptions from providing a statement of advice". Only three ROA situations have been found. The
fourth may be a different exemption entirely rather than a fourth ROA basis — recorded so nobody
re-derives the question, and it does not change the three above.

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

**The `advice_record_role` field is the seam.** It is a boolean: `true` on `soa` and `roa`, `false`
on every other type. Logic that needs "the advice record" keys on the role, never on the label
"SOA". `car` is deliberately **not** a document type while Tranche 2 is unlegislated (decided
5 Sep 2026, recorded in the knowledge base's `reform_watch`). When it is enacted, adding a `car`
entry with `advice_record_role: true` is a data change — no Python.

---

## 6. Master mapping table (the classification engine)

Document type is the spine. The classifier identifies `doc_type` from content, looks up the row,
and that row populates advice type, process stage, compliance step, and flag behaviour.

| doc_type (KB id) | Advice type implied | Process stage | Safe harbour step | Legal basis | advice_record_role | Flag behaviour |
|---|---|---|---|---|---|---|
| FSG (`fsg`) | Any advice relationship | Initial consultation | Pre-step | s941A | `false` | None expected |
| Fact find (`fact_find`) | Personal advice (input) | Discovery | Steps 1–2 | s961B(2)(a)–(b) | `false` | None; absence upstream of SOA = flag |
| Risk profile (`risk_profile`) | Personal advice (input) | Discovery | Steps 1–2 | s961B(2)(b) | `false` | None; pairs with fact find |
| File note (`file_note`) | Personal advice (working) | Advice construction | Steps 3–6 | s961B(2)(c)–(f); s912G | `false` | None; never the advice itself |
| SOA (`soa`) | New personal advice | Advice delivery | Step 7 | s946A | `true` | Sub-type: comprehensive vs scaled/limited |
| ROA (`roa`) | Personal advice, under one of 3 situations | Advice delivery / ongoing | Step 7 | reg 7.7.10AE · reg 7.7.10AAA (notional s946B(7)–(8)) · s946AA | `true` | **Medium: confirm which of 3 situations** |
| ATP (`authority_to_proceed`) | Implementation authority | Implementation | Post-advice | follows SOA/ROA | `false` | None; should follow an SOA/ROA |
| FDS (`fee_disclosure_statement`) | Ongoing service | Ongoing review | Post-advice (annual) | s962H | `false` | Era check (pre/post DBFO Tranche 1) |
| PDS (`pds`) | General (product info) | Any (reference) | Not a safe-harbour doc | s1013 | `false` | None; product-issuer doc |

**Not yet document types** (a firm has them, the knowledge base does not model them — issue #23):
application / insurance forms (implementation stage, s1012) and engagement letters (initial
consultation). Bella added on 13 Oct 2026: emails, letters of outcome from government,
invoices, ID documents, tax returns, and provider forms. They route to review today rather
than being classified.

### The three load-bearing rows
- **SOA/ROA** — the only documents that *are* safe-harbour evidence (step 7). Everything else
  feeds in or flows out. This is why clustering works: the SOA is the centre of an advice event.
- **ROA** — three situations → the engine can't stop at "ROA, done"; it raises the
  confirm-which-kind flag. This is what makes it domain-aware rather than a dumb type-detector.
  And the situation is separate from what the advice recommends: conflating the two is the
  mistake #33 corrected.
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
- ROA situations — Corporations Regulations 2001 (reg 7.7.10AE, 7.7.10AAA, 7.7.09A) and
  Corporations Act (s946B, s946AA); ASIC INFO 266 and its FAQ page "FAQs: Records of Advice
  (ROAs)", whose Table 1 lists the three situations verbatim
- Example advice documents — ASIC RG 90 (SOA), INFO 267 (limited-advice SOA), INFO 266 (ROAs)
- DBFO reform — Treasury DBFO package; ASIC DBFO page; Treasury Laws Amendment (DBFO) Act 2024
  (Tranche 1); Tranche 2 exposure draft (Mar 2025); industry commentary (Hamilton Locke, KWM,
  Professional Planner, IFA) on status and scope

**Note on currency:** DBFO is live, moving legislation. Verify the Tranche 2 Bill's current status
before using any DBFO claim in a pitch or compliance context.
