# sample_documents.json — Labelling Brief (unit 2)

**Purpose:** hand-label each sample file's *expected* result so `harness.py` can be scored
against ground truth. This is the human-labelled truth set — the classifier's answers are
graded against these, so accuracy of *these labels* matters more than anything.

**Owner:** the domain collaborator. Not to be inferred from filenames by the developer or the model.
**Last updated:** 2026-08-20.

---

## Guiding principle for this test set

Test the **document types advisers actually handle in volume**, not niche edge cases. The
everyday advice-firm pile — the types that flow through essentially every client file — is the
priority. Rare variants (e.g. stockbroker ROA, a specific ethical-super PDS) are kept only
because they were free and legal to source; they are not the point of the set.

**We are labelling what we have now so the harness runs today.** The genuinely high-volume
everyday types we are still missing are flagged in §3 as the next sourcing job — see there.

---

## 1. Schema (per file)

Each entry in `sample_documents.json` should carry at least:

```json
{
  "file": "SOA_RG90_scaled_advice.pdf",
  "expected_doc_type": "SOA",
  "expected_advice_record_role": "SOA",
  "expected_flags": [],
  "notes": "ASIC RG 90 teaching sample. Scaled personal insurance advice, new client.",
  "is_real_client_file": false
}
```

- `expected_doc_type` — the type the classifier must return.
- `expected_advice_record_role` — the DBFO seam value (SOA today; becomes CAR post-Tranche 2).
- `expected_flags` — flags the classifier *should* raise (empty = clean classification expected).
- `is_real_client_file` — `false` for ASIC/regulatory samples. Reminds everyone the set is not
  yet representative of real practice documents.

---

## 2. Expected labels for the current files

| File | expected_doc_type | advice_record_role | expected_flags | Notes |
|---|---|---|---|---|
| `SOA_RG90_scaled_advice.pdf` | SOA | SOA | (none) | RG 90 scaled advice, new client, personal insurance |
| `SOA_INFO267_limited_advice.pdf` | SOA | SOA | (none) | INFO 267 limited-advice example SOA |
| `ROA_INFO266_att1_retain_modify.pdf` | ROA | n/a | `confirm_roa_basis` | Further-advice basis (reg 7.7.10AE). Republished Nov 2024 |
| `ROA_INFO266_att2_nochange.pdf` | ROA | n/a | `confirm_roa_basis` | **No-change / no-action basis (s946B(7))** — NOT further advice. Republished Nov 2024 |
| `ROA_INFO266_att3_stockbroker.pdf` | ROA | n/a | `confirm_roa_basis` | Stockbroker switch. Edge variant, kept but not core |
| `FSG_PeninsulaWealth.pdf` | FSG | n/a | (none) | Boutique advice-practice FSG |
| `FSG_UniSuper.pdf` | FSG | n/a | (none) | Large super-fund FSG — structurally different from Peninsula |
| `PDS_AustralianEthicalSuper.pdf` | PDS | n/a | (none) | Edge variant (ethical super). Kept but not core |
| `PDS_<fund>.pdf` | PDS | n/a | (none) | Second PDS — issuer TBD, low priority |

**The `confirm_roa_basis` flag is expected and correct on all three ROAs.** An ROA legitimately
has four legislative bases, so the right behaviour is a medium-severity "confirm which kind,"
not a clean silent classification and not an error. If the classifier returns an ROA with *no*
basis flag, that's a miss — log it.

**Attachment 2 label is the one to get right.** It is a *no-change* ROA. The earlier filename
implied "further advice," which was wrong. Att 1 = further advice, att 2 = no-change,
att 3 = stockbroker. Three distinct bases across the set; the fourth (small investment,
reg 7.7.10AAA) is not present and is a known gap, not something to fake.

---

## 3. Missing everyday types — next sourcing job (do not forget)

The current set is heavy on ASIC regulatory samples because those were free and legal to source.
But the **highest-volume everyday document types are not yet in the set at all.** These flow
through nearly every real client file and matter more for representativeness than a second PDS:

- **Fact find** — client data-capture document. Extremely common; highly variable in layout.
- **Engagement letter** — scope/terms of the advice engagement.
- **FDS (Fee Disclosure Statement)** — recurring, templated, high volume.
- **ATP (Authority to Proceed)** — the client sign-off that follows an SOA.

**Action:** source 1–2 de-identified real examples of each before claiming the test set is
representative. These are better sourced from a pilot firm (de-identified) than from the web,
because real-world layout variety is exactly what the classifier needs to prove itself against.
Until then, treat any missing-type result from the harness as untested, not as a pass.

---

## 4. Manual checks that are NOT the developer's job (the domain collaborator owns these)

Before a file is trusted in the set:
- Confirm the PDF is **native selectable text**, not a scanned image or a blocked-download error
  page. (A blocked download is a tiny file that opens as an error, not a PDF.) The ASIC files
  download clean in a browser; the FSG/PDS issuer sites are the ones with bot protection —
  browse from the issuer's disclosure-library page rather than deep-linking the PDF.
- Confirm the two FSGs are structurally different enough to be a real test (they are — boutique
  practice vs large super fund differ in remuneration/associations sections).
