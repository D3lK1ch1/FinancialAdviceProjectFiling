# Which document is for what

**Bella's decisions and open questions live in one place: GitHub issue #61.** They are
also written into `knowledge_base.json` (the rules the tool reads) and
`GROUND_TRUTH.md` ("Settled domain answers"). Other documents link there rather than
repeating them. GitHub issues are for work to do; questions go in #61.

| Document | What it's for | Who keeps it |
|---|---|---|
| `GROUND_TRUTH.md` | How the system works, rule by rule, and every settled domain answer | Delia, with Bella's answers |
| `SYSTEM.md` | The spec: what the tool does and the filing layout | Both |
| `UI_INTEGRATION.md` | How the React screens join the Python backend; the gaps | Both |
| `advice_classification_reference.md` | The domain research behind the knowledge base: types, stages, legal bases | Bella |
| `reference/` | Research data: implementation forms taxonomy, sample coverage | Bella |
| `sample_documents.labelling.md` | The expected answer for each sample file, to grade the tool against | Bella |
| `EXPERIMENT_LOG.md` | Classifier changes measured on the samples, with the numbers | Delia |
| `BUSINESS_CASE.md` | Why this is worth building: the gap, customers, pricing, what evidence is still needed | Bella |
| `archive/` | The August drafts: product, architecture, first handover. History, partly out of date | n/a |

Outside `docs/`: `CLAUDE.md` (standing rules for Claude), `CHANGELOG.md` (what changed,
newest first), `README.md` (how to run it), `frontend/README.md` (the React screens).
