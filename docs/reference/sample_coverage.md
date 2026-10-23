# Sample coverage: what the public sample set can and can't cover

Moved from GitHub issue #35 on 21 Oct 2026, because it is a record rather than work to
do. Text kept as written, with its later updates at the end. New sample work (provider
implementation forms) is in #74 and `implementation_forms.json`.

> **Status — 6 Oct.** A record, not a task. Refreshed to match the corrected ROA model (three situations, not four — #33) and to add what the sample set has shown since 17 Sep. Closes when a pilot firm provides real documents, or stays open as the record of why it could not.

## Coverage at a glance

One row per document type in `knowledge_base.json` (`documents[].id`).

| KB id | Real public example? | What we have | Why nothing better |
|---|---|---|---|
| `soa` | Yes, annotated | 3 ASIC examples (RG 90 2013, RG 90 + ATP, CP 284) | Firms don't publish client SOAs |
| `roa` | Yes, annotated — **1 of 3 situations** | 3 ASIC INFO 266 attachments, all further advice | See below |
| `authority_to_proceed` | Appended only | 1 real (appended to RG 90 SOA); standalone is mocked | A standalone ATP is never published |
| `fsg` | Yes | Published issuer FSGs | — |
| `pds` | Yes | 3 UniSuper PDSs (owner-locked — readable since #44) | — |
| `fact_find` | Blank templates only | 2 (Foundation FP 2024, Interprac 2018) | A filled-in one holds a client's details |
| `risk_profile` | Blank templates only | 5 questionnaires | Same |
| `file_note` | **None — not mocked either** | — | Firm-internal, free-form, client-specific |
| `fee_disclosure_statement` | No | 2 mocks (pre/post DBFO Tranche 1) + a scanned one | Client-specific, never published |

## The rule we are working to

If a type or category has no real public example, **say so and stop** — no mock written to fill the hole. A mock is written by the same person who wrote the rules that read it, so it matches by construction and reports success. The gap is recorded in three places: `samples/SOURCES.md`, the `example_status` fields in `knowledge_base.json` (`documents[roa].legislation.situations[].example_status`), and here.

## ROA situations — 1 of 3 covered, three times over

| `situations[].id` | Real example | Why not |
|---|---|---|
| `further_advice` (reg 7.7.10AE) | **Yes ×3** | — |
| `no_buy_sell` (s946B(7) / reg 7.7.10AAA) | No | ASIC published no example of this situation |
| `small_investment` (s946AA, under $15,000) | No | Att 3 ("Stockbroker") was assumed to be this from its title; its text has neither "s946AA" nor "small investment", and it cites reg 7.7.10AE |

Att 2 is titled "No change advice", but "no change" is what it *recommends*, not the situation that permits it — it relies on further advice because the client had a 2018 SOA. (The earlier "hold / no action" row is gone: it was never a separate situation. #33.)

## What the documents we *do* have can't tell us

1. **Annotated text.** All three ASIC ROAs carry guidance in a side column that extracts inline, so a phrase may be ASIC explaining the law rather than an adviser advising. Half of why #32's first flag misread att 1. Anything calibrated on these needs re-checking against the first real firm ROA.
2. **Signals that aren't distinctive (found 19 Sep).** With three documents of one kind there are no negative examples, so you can't tell a signal that *identifies* a category from one that merely *appears* in it:
   - "further advice" appears in all three ASIC **SOAs**
   - "remain invested" fires on a risk-profile questionnaire
   - "Statement of Advice dated" fires on the standalone ATP mock
3. **One good file masked three bad ones.** `PDS.pdf` parsed fine while all three UniSuper PDSs failed (owner-password encryption, fixed in #44). A type is not covered because one file of that type works.
4. **Silent partial extraction.** `parse_pdf()` warns "Rotated text discovered. Output will be incomplete" on the FSG and two UniSuper PDSs; it goes to stderr and nothing surfaces it. Not yet its own issue.
5. **Blank templates can't test anything that depends on content.** No names, dates or signatures — so client identity (#6), date extraction (#8, #48) and advice-event grouping are untested on real input.

## Why this is worth keeping

1. **The hardest types to classify are exactly the ones nobody publishes.** FSGs and PDSs are public and standardised; file notes, ATPs, ROAs and FDSs are firm-internal and vary by firm. Available evidence is inversely correlated with difficulty.
2. **Regulator examples are annotated, and annotation is not neutral.** Anyone building on ASIC examples will hit this and probably not notice.
3. **It limits what can be claimed before a pilot.** Two of three ROA situations, `file_note`, and every filled-in fact find / risk profile are untested against anything real. That is the honest answer to "how accurate is it?" — better than a number from documents we wrote ourselves.

Related: #33 (situation count), #32 (`example_status`), #44 (encrypted PDFs), #23 (types a firm holds that the KB doesn't model), #48 (dates on real SOAs).


### Update from issue #35 by Bella (ahaythorpe), 2026-09-17:
**Two more evidence limits, found while chasing #36.** Both are the same shape as the ones above — the sample set told us something only because we ran it, not because we read it.

## Encrypted PDFs looked like "no sample" and were actually "cannot open"

All three UniSuper PDS files failed to parse. It read like a gap in the set. It was not: they are AES-encrypted with an owner password, which is the ordinary way a product issuer publishes a PDS while restricting printing and copying. A missing dependency, not a missing document — see #36.

The reason it went unnoticed is worth keeping: **`PDS.pdf` in the working copy is unencrypted and parses fine.** One good example masked three broken ones, and the sample set looked healthier than it was. A type is not covered because one file of that type works.

## Signals learned from the documents we have are not distinctive

Running #32's ROA basis signals across every document available:

- **"further advice" appears in all three ASIC *SOAs*** — RG 90 2013, RG 90 with ATP, and CP 284. It is the strongest further-advice signal we have and it is not unique to ROAs at all.
- **"remain invested" fires on a risk-profile questionnaire.**
- **"Statement of Advice dated" fires on the standalone ATP mock** — correctly, since that is what an ATP does, but it means the phrase says "this document references an SOA", not "this document is further advice".

None of these is currently a bug, because the flag only runs on documents the classifier calls an ROA. But it means the signals are doing less work than their hit rate suggests: they are common advice-document language, and they were only ever validated on documents already known to be ROAs.

**The general point for the write-up:** with three real documents of one kind, you cannot tell a signal that identifies a category from a signal that merely appears in it. That needs negative examples — documents of the *other* bases — which is exactly what the set does not have.

## Also worth recording

`parse_pdf()` emits **"Rotated text discovered. Output will be incomplete"** on the FSG and on two of the three UniSuper PDSs. The extraction is silently partial and nothing surfaces it — the warning goes to stderr and the pipeline carries on as if the text were complete. Not raised as its own issue yet; it belongs with #36's fail-soft work if that is taken up.

### Update from issue #35 by Bella (ahaythorpe), 2026-10-05:
**6 Oct — searched for the two missing ROA situations. Outcome: none exist publicly; recorded, not mocked.**

**Searched:** ASIC (FAQ, INFO 266, media releases), AustLII, industry sources. No real or example ROA for `no_buy_sell` or `small_investment`. The only template found is a paid legal-firm product.

**Why `no_buy_sell` is the hardest to source:** ASIC's FAQ says a no-buy/sell ROA need not be given to the client unless they ask — it stays on the adviser's file. If the client usually never sees one, a public example is close to impossible. ([ASIC FAQ](https://www.asic.gov.au/regulatory-resources/financial-services/giving-financial-product-advice/faqs-records-of-advice-roas))

**Signals run on every ASIC ROA available** (`flags._roa_basis_unconfirmed`, main @ 79539eb):

| File | Proposed | Matched |
|---|---|---|
| INFO 266 att 1 | `further_advice` | "further advice" |
| INFO 266 att 2 | `further_advice` | "further advice" |
| INFO 266 att 3 | `further_advice` | "further advice" |
| ASIC COVID-19 relief example ROA (Jul 2021) | `further_advice` | "further advice" |

The COVID ROA relied on a temporary ASIC relief that ended 15 April 2022, so it is a historical case, not a fourth situation — and it is probably the "fourth exemption" in `legislation.unresolved`.

**Two gaps, left as gaps:**
- **`no_buy_sell` — the no-fee condition has no signal.** The decisive test is that no fee or benefit was received, but nobody on the project knows how a real ROA words that, so no phrase is added. Until a real one arrives, this situation can only be confirmed by a reviewer.
- **`small_investment` — keep `inferred` empty.** The COVID ROA contains "$15,000" as an *income shortfall*, not an investment amount. A dollar-figure signal would fire on it wrongly; only a document naming its own basis ("small investment advice", "s946AA") should count.

No code change proposed.

