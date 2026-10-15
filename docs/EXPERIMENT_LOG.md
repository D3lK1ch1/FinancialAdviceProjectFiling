# Experiment log

A record of changes to the classifier that were measured against the sample
documents: what was changed, what the numbers were, and what they showed.
`CHANGELOG.md` gets one line per outcome and points here. Nothing in this file
changes how the app behaves.

**How a run works.** Every PDF in `samples/` goes through the same steps as
`/ingest`: parse → scope gate → classify → verify. For each file, a run records:

| Field | Meaning |
|---|---|
| `doc_type` | the classifier's answer |
| `confidence_raw` | the model's own confidence |
| `confidence` | the verified figure the review threshold applies to (`confidence.py`) |
| `missing` | quotes the model gave as evidence that aren't in the document text |

Verified confidence = model confidence × (quotes found ÷ quotes given) × scope
agreement. A document needs **0.90** to skip review.

**Environment.** `llama3.1` 8B (Q4_K_M) on Ollama, 4096-token context.
Ollama 0.40.3 on 14 Oct and 0.40.4 on 15 Oct. It updated itself in between (see finding 9).

---

## #59 — Classifier evidence must be exact quotes (14–15 Oct 2026)

**Status:** in progress. The pass bar isn't met yet.

### Problem
`confidence.py` checks each quote the classifier gives as evidence
(`matched_signals`) against the document's text, and lowers confidence for every
quote it can't find. The model often returned summaries or field labels instead
of quotes, so correct answers were marked down and sent to review.

### Pass bar
- INFO 267 and FSG_UniSuper keep the right type with verified confidence ≥ 0.90.
- `missing` empty or nearly empty.
- No wrong-type answer gains confidence.
- `confidence.py` is not loosened. The fix belongs in what the classifier is asked for.

### Change 1 — the prompt asks for exact quotes
`classifier.py` `_build_prompt()`:

| | Before | After |
|---|---|---|
| Evidence instruction | "short phrases actually present in the document text … (e.g. a title phrase, **a key field you found**)" | "3-6 exact quotes, each under 12 words, copied character for character from the Document text … never a field label", plus right and wrong examples |
| Hints heading | `Classifier hints:` | `Hints (descriptions of each type, NOT text to quote):` |

The old wording "a key field you found" invited field labels ("fees/commissions")
as evidence.

**Result (one run per prompt, default sampling):**

| File | Before conf / missing | After conf / missing |
|---|---|---|
| FSG_AustralianSuper | 0.38 / 3 | 0.92 / 0 |
| FSG_PeninsulaWealth | 1.00 / 0 | 0.99 / 0 |
| **FSG_UniSuper** | 0.45 / 1 | **0.50** / 2 ✗ |
| PDS_AustralianEthicalSuper | 0.44 / 5 | 0.999 / 0 |
| PDS_AustralianSuper | 0.49 / 3 | 0.57 / 3 |
| ROA_INFO266_att1_retain_modify | 0.80 / 0 | 0.32 / 3 |
| ROA_INFO266_att2_nochange | 0.76 / 1 | 0.95 / 0 |
| ROA_INFO266_att3_stockbroker | 0.90 / 0 | 0.33 / 2 |
| **SOA_INFO267_limited_advice** | 0.41 / 4 | **0.57** / 2 ✗ |
| SOA_RG90_scaled_advice | 0.63 / 2 | 0.80 / 0 |

Every file kept its correct type. These are single runs under random sampling,
so only the large swings mean anything (finding 5).

### Change 2 — temperature 0
`classify()` now sends `"options": {"temperature": 0}` to Ollama.

**Result:** two files were each classified twice directly, and the same files
were uploaded through the app once. All three outputs were identical, for both files.

| File | Model's answer (every time) | Verified |
|---|---|---|
| FSG_AustralianSuper | fsg 0.9, the same 5 quotes | 0.18 (1 of 5 found) |
| ROA_INFO266_att2_nochange | roa 0.8, the same 4 quotes | 0.80 |

A full 10-file baseline at temperature 0 is still to be run.

### Change 3 — short quotes, no examples
`_build_prompt()`: the `Right:` and `Wrong:` example lines are gone. The quote
instruction became "3-6 short quotes, each 3 to 8 words, copied exactly … same
words, same punctuation. Prefer headings, titles and labelled lines … If you
cannot copy a phrase exactly, leave it out." Temperature 0.

| File | Conf / missing | Model's own conf | Limited by |
|---|---|---|---|
| FSG_AustralianSuper | 0.18 / 4 | 0.9 | missed quotes (PDF columns, apostrophe) |
| FSG_PeninsulaWealth | 0.75 / 1 | 0.9 | 1 missed quote |
| **FSG_UniSuper** | **0.40** / 3 ✗ | 0.8 | missed quotes, all PDF columns (finding 10) |
| PDS_AustralianEthicalSuper | 0.72 / 1 | 0.9 | 1 missed quote |
| PDS_AustralianSuper | 0.95 / 0 | 0.95 | — |
| ROA_INFO266_att1_retain_modify | 0.80 / 0 | 0.8 | model's own confidence |
| ROA_INFO266_att2_nochange | 0.80 / 0 | 0.8 | model's own confidence |
| ROA_INFO266_att3_stockbroker | 0.67 / 1 | 0.8 | 1 missed quote |
| **SOA_INFO267_limited_advice** | **0.90** / 0 ✓ | 0.9 | — |
| SOA_RG90_scaled_advice | 0.80 / 0 | 0.8 | model's own confidence |

FSG_UniSuper timed out (180 s) in the full run. It was retried on its own and finished in 41 s.

- **INFO 267 passes** at exactly 0.90, with every quote found.
- **The copied example is gone** from every file (finding 3 fixed).
- **The word limit is still ignored.** Many quotes run 10–20 words.
- **Three files are capped by the model's own confidence** (0.8), not by missed
  quotes. That's outside #59, which is about the evidence check.

**10. PDF columns are now the main cause of missed quotes.** All three FSG_UniSuper
misses are honest quotes that the text extraction broke apart. For example:
`We can help you design a personal financial plan` is extracted as
`…We can help you design a personal\n      name of UniSuper Advic…`,
with the next column's line interleaved. The model reads the sentence as a person
would; the extracted text doesn't hold it that way.

The parser's "Rotated text discovered. Output will be incomplete" warning on the
FSGs is a separate problem (#35, point 4). The missed FSG quotes that were checked are
*present* in the extracted text, just split up, not dropped. For example:
`What financial services are available\nraised in this FSG, please ask us.   to   m…`.
Multi-column layouts are typical of issuer-published FSGs and PDSs. Whether a
firm's own documents are laid out this way can't be told from public examples (#35).

### Findings

**1. Summaries mostly stopped.** Before: `"adviser + AFSL/authorised-rep number:
Susan Deng, ABC Advice Pty Ltd"`. After: `"The client, John Patel, has sought
advice"`, a real sentence from the document.

**2. Labels still slip through sometimes.** PDS_AustralianSuper:
`"fees and costs template"`, `"effective date"`. FSG_AustralianSuper:
`"fees/commissions"`, `"licensee name"`.

**3. The model copies the prompt's example.** `"Our fees are $3,300"` comes
from the prompt, not any sample. It was returned for INFO 267, and again later
for FSG_PeninsulaWealth and FSG_AustralianSuper. A similar made-up line, `"Our
fees are not mentioned"`, appeared for ROA att2. Any concrete example in a
prompt is text the model can echo back.

**4. Near-quotes fail the check.** The model rewrites quotes from memory, so
small slips turn real quotes into `missing`:

| Model returned | Document says | Slip |
|---|---|---|
| `ROA: Stockbroker` | `(ROA): Stockbroker` | dropped a bracket |
| `SOA can be used instead of a Statement of Advice` | `an ROA can be used instead of a Statement of Advice` | wrong word |
| `client name, Nick Rossi` | `The client, Nick Rossi` / `Client name: Nick Rossi` | blended two lines |
| `remuneration, our key relationships…` | `are remunerated, our key relationships…` | changed word |
| `AustralianSuper's services…` | `AustralianSuper’s services…` | straight vs curly apostrophe |
| `…licensed to provide a superannuation trustee service` | sentence split across two PDF columns | not continuous in the extracted text |

Longer quotes slip more. The FSG_AustralianSuper misses were 14–19 words long,
despite "under 12 words" in the prompt. ROA att1 and att3 *dropped* after
change 1 for this reason: the old prompt drew short title phrases, which the
model copied correctly.

The check is all-or-nothing per quote, so a one-character slip costs as much as
an invented quote. That's deliberate: loosening it would hide invented quotes.
Two of the slips are about typography rather than honesty (apostrophe style, PDF
columns). They're recorded as calibration evidence; `confidence.py` is unchanged.

**5. Default sampling is noisier than the effect being measured.** Under
Ollama's default settings, the same prompt on the same file scored 20–44 points
apart between runs (INFO 267: 0.57 vs 0.87, FSG_AustralianSuper: 0.92 vs 0.48).
Change 2 removed this.

**6. Repeatable isn't the same as accurate.** At temperature 0 the model gives
its *most likely* answer every time. For FSG_AustralianSuper that answer is long
quotes with slips, so it now scores 0.18 on every run. The value of change 2 is
a fixed baseline: any later difference comes from the prompt, not from chance.

**7. The prompt nearly fills the context window (a risk; not shown to cause anything yet).**

| Sample | Prompt tokens (of 4096) | Room left for the answer |
|---|---|---|
| SOA_INFO267_limited_advice | 3,953 | ~140 |
| FSG_UniSuper | 3,416 | ~680 |

Most of the prompt is the indented hints JSON plus up to 6,000 characters of
document. A JSON answer with 6 quotes can need 100–200 tokens. When the window
fills, Ollama drops tokens without warning. Possible fixes: a larger `num_ctx`,
compact hints JSON, or less document text. Each changes what the model sees, so
measure each one separately.

**8. Regulator annotations count as evidence.** INFO 267 returned `"We have
annotated this example SOA"` and `"How to read the example SOA"`. That's ASIC's
commentary, not SOA content (#35). The quotes are real, so they pass the check,
but a firm's own SOA wouldn't contain them.

**9. The runtime changed without being asked.** Ollama updated itself from 0.40.3 to 0.40.4
between 14 and 15 Oct. The model digest (`46e0c10c…`) stayed the same, but the
engine still changed under the results.

### Follow-ups outside #59 (for #7)
- Stamp the Ollama version, model digest and context size on results (findings 7, 9).
- `classify()` discards Ollama's error message: `raise_for_status()` reports only
  "500 Server Error", and Ollama's explanation in the response body is lost.

### Next for #59
1. A full 10-file baseline at temperature 0, run twice to confirm it repeats.
2. Prompt pass 2: remove the concrete example (finding 3); ask for short quotes
   of 3–8 words, ideally headings or titles (finding 4).
3. Re-judge against the pass bar. Any correct file still under 0.90 gets its
   reason recorded here.
