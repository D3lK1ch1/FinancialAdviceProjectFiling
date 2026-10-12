# HANDOVER.md — Sample Prep & Docs Handover

**To:** developer / data scientist.
**From:** the domain collaborator.
**Date:** 2026-08-20.
**Read order:** this file → `SYSTEM.md` (spec) → `CLAUDE.md` (ground rules) →
`sample_documents.labelling.md` (unit 2).

This resolves the "Sample Prep (Human Portion)" TODO. It records the judgment calls that are
made, and states plainly what is still a manual human step (and why it can't be scripted).

---

## Status of the TODO

| TODO item | Status | Who / note |
|---|---|---|
| 1. Fill the PDS gap (2nd PDS) | **Open, low priority** | Manual browser download. Second PDS is an edge variant — not blocking |
| 2. Spot-check every file is native text | **Manual — domain collaborator** | Human eyeball check; can't be scripted. See §2 |
| 3. Narrow down the test set | **Decided** | See §3 — labels + keep/drop resolved |
| 3a. Does the ROA set test the four bases? | **Answered** | 3 of 4 bases covered; enough to prove the mechanism. See §3 |
| 3b. Are the two FSGs different enough? | **Answered** | Yes — boutique vs large super fund differ structurally. Keep both |
| 3c. Anything to drop as unrepresentative? | **Answered** | Nothing dropped; the *gap* is missing everyday types, not bad files. See §4 |
| 4. Label expected doc_type (unit 2) | **Drafted** | `sample_documents.labelling.md` — domain collaborator to confirm |

---

## 1. Source URLs (ASIC files download clean in a browser)

The ASIC files are **not** bot-protected — they serve straight to a normal browser. The
bot-blocking hit earlier was on the super-fund / practice sites, not ASIC.

**SOAs**
- `SOA_RG90_scaled_advice.pdf` — https://download.asic.gov.au/media/4567144/rg90-published-7-december-2017.pdf
- `SOA_INFO267_limited_advice.pdf` — https://download.asic.gov.au/media/ywsgxnxe/attachment-to-info-267-published-1-december-2021.pdf

**ROAs** (att 1 & 2 republished Nov 2024 — newer than the old filenames implied)
- `ROA_INFO266_att1_retain_modify.pdf` — https://download.asic.gov.au/media/sq4l3vw4/info-266-attachment-1-published-21-november-2024.pdf
- `ROA_INFO266_att2_nochange.pdf` — https://download.asic.gov.au/media/h1obcqsh/info-266-attachment-2-published-21-november-2024.pdf
- `ROA_INFO266_att3_stockbroker.pdf` — https://download.asic.gov.au/media/qzzaehfj/info-266-attachment-3-published-5-november-2021.pdf

**FSG / PDS** — issuer sites have bot protection. Browse from the issuer's disclosure-library
page and Save As, rather than deep-linking the PDF (deep links are what trip the protection).

---

## 2. Why item 2 stays manual

Confirming a file is native selectable text — not a scanned image or a blocked-download error
page — is a human eyeball check. A blocked download is a tiny file that opens as an error page,
not a PDF. Open each PDF, try to highlight text. This can't be delegated to code or the model;
it's the check that the *input* is real before anything downstream trusts it.

---

## 3. Judgment calls (resolved)

- **Attachment 2 relabelled:** it is a **no-change ROA**, not "further advice." Corrected
  filename: `ROA_INFO266_att2_nochange.pdf`. Att 1 = further advice, att 2 = no-change,
  att 3 = stockbroker.
- **ROA bases:** the set covers **three of four** legislative bases. That is enough to prove the
  "confirm which kind" mechanism. The fourth (small investment, reg 7.7.10AAA) is a **known gap**,
  logged — not to be sourced artificially just for completeness.
- **FSGs:** keep both. Boutique practice (Peninsula) vs large super fund (UniSuper) differ in
  structure and wording — a genuine test, not a trivial one.

---

## 4. The real gap: everyday high-volume types

The set is heavy on ASIC regulatory samples (free, legal to source). The document types advisers
handle in the highest volume are **not in the set yet**: fact find, engagement letter, FDS, ATP.
These matter more for representativeness than a second PDS. **Next sourcing job:** get 1–2
de-identified real examples of each, ideally from a pilot firm. Until then, the harness is
testing type-detection on regulatory samples only — fine to run today, not yet representative.
Full detail in `sample_documents.labelling.md` §3.

---

## 5. What ships in this handover

- `SYSTEM.md` — the spec / source of truth.
- `CLAUDE.md` — standing ground rules Claude Code reads every session.
- `sample_documents.labelling.md` — unit 2 labelling brief (expected doc_type per file).
- `HANDOVER.md` — this file.

**Caveat on SYSTEM.md:** it was reconstructed from project history and may be missing wording
added since. Diff it against the SYSTEM.md in the live project folder and merge rather than
overwrite if the local copy has more detail.
