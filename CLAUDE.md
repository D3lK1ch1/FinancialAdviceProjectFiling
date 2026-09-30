# CLAUDE.md — Advice Document Classifier & Filing System

*Claude Code reads this file automatically every session and treats it as standing
instructions. Keep it short and true. When the design changes, update it and SYSTEM.md
together.*

## What this project is
A tool for Australian financial-advice firms. It reads client documents (PDF/Word),
identifies what each one is (SOA, ROA, FSG, fact-find, etc.), proposes where to file it
and what to rename it, and flags anything it can't confidently place for human review.
It proposes; a human approves, edits, or rejects. It classifies documents that already
exist — **it never generates financial advice.**

## Read these first
- `docs/SYSTEM.md` — the spec. Build from it. Source of truth for behaviour.
- `knowledge_base.json` — the domain data the classifier reads (v0.3).
- `harness.py` — a working keyword-based prototype of the full pipeline. Reference, not final.
- `docs/sample_documents.labelling.md` — hand-labelled expected results for the sample files in
  `samples/`. Note: `harness.py` currently tries to load `sample_documents.json`, which doesn't
  exist — that mismatch predates this reorg and is tracked as a known gap, not fixed here.

## Documentation
Planning, spec, and handover documents live in `docs/` (PRD, architecture, business case,
system spec, session notes, to-do list). Everything in the project root is either code the
app runs, data it reads (`knowledge_base.json`), or sample input (`samples/`).

## Ground rules (do not break these)
1. **The knowledge base is the source of truth for document rules.** Read document types,
   classifier hints, stages, and flags from `knowledge_base.json`. Never hardcode document
   rules in Python — if a rule is missing, add it to the knowledge base, not the code.
2. **Everything is a proposal a human approves.** Never file silently. On low confidence,
   route to `_Needs review` with a reason. Confidence must be visible.
3. **Keep the storage layer abstracted.** Filing must swap from local folder to cloud bucket
   later without touching the classifier. No storage details baked into classification logic.
4. **Keep the three settings independent:** display mode (teach/don't), filing mode
   (client+event nesting), and the classification engine. They must not depend on each other.
5. **Build one step at a time and run after each change.** Small, testable pieces. Do not
   generate the whole system at once. Read what broke before moving on.
6. **Maintain a failure log.** Every misclassification: input, tool's answer, correct answer,
   one-line why. This is the improvement loop and the proof of accuracy.

## Domain facts that are easy to get wrong
- **An ROA is permitted in three situations, not one:** further advice (notional s946B(2)-(3)
  via reg 7.7.10AE), no buy or sell product advice (notional s946B(7)-(8) via reg 7.7.10AAA),
  and small investment advice under $15,000 (s946AA + reg 7.7.09A). So an ROA is a
  medium-severity "confirm which kind" flag, **not** a high-severity error.
- **Three, not four — this was corrected on 17 Sep 2026 (issue #33).** The old list carried
  "hold/no-action (s946B(7))" and "no buy/sell (reg 7.7.10AAA)" as separate bases. They are
  one situation: s946B(7) *is* the no-buy/sell provision, and reg 7.7.10AAA substitutes a
  notional version of it and sets its content rules. ASIC's own FAQ lists three.
- **"Hold" is not a basis. It is what the advice recommends.** Which situation permits the
  ROA and what the advice says are two different things, and collapsing them is the mistake
  that made the old list wrong. An ROA can be *further advice* whose *recommendation* is no
  change — which is exactly what INFO 266 attachment 2 is.
- **Situation 2 has a limb people forget:** no remuneration or benefit received, and
  conflicts disclosed. For a client on an ongoing fee arrangement that usually fails, which
  is why an annual-review "no change" recommendation is normally documented as further
  advice. Content alone never establishes that basis.
- **`advice_record_role`** in the data model is the DBFO SOA→CAR seam. It is load-bearing.
  Do not delete it as unused.
- **All three INFO 266 example ROAs cite the further-advice situation** — including
  attachment 2, titled "No change advice", which relies on it because the client had an SOA
  from 2018, and attachment 3 ("Stockbroker"), which mentions neither s946AA nor "small
  investment". The sample set covers one situation three times, not three situations once.
  An earlier version of this file said att 2 was "not further advice"; that was wrong.

## What NOT to do
- Do not build the AI summary feature until classification + event-grouping are reliable.
- Do not set up cloud infrastructure yet — this phase is local, filing to a local folder.
- Do not generate or recommend financial advice. The tool describes documents that exist;
  it never creates advice content.

## Build sequence (current position: step 3)
1. [done] Knowledge base
2. [done] Test harness
3. [now] Real documents through the harness; fix failures; calibrate confidence
4. Swap keyword matcher for LLM classifier (same hints)
5. Approve/Edit/Reject UI
6. Local → Australian-region cloud storage (only when a pilot needs it)
7. AI summary per advice event (only when grouping is trusted)
