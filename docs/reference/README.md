# Reference data

Research material the knowledge base and tests draw on. Not rules: a rule only
counts once it is in `knowledge_base.json` (ground rule 1).

## implementation_forms.json

Bella's taxonomy of the provider forms that implement advice (compiled 21 Oct 2026):
13 kinds, from opening an account and rolling over super to beneficiary
nominations, contributions, insurance, fee consent, debt recycling and share
registry. Each kind has a description, the keywords that identify it, and example
forms with links. Providers covered: BT Panorama, Rest, Hostplus, MUFG, Leveraged
Equities and the ATO.

- **Links change.** Treat each URL as a starting point and check it before relying
  on it.
- **`verify: true`** means the entry came from general industry knowledge, not a
  document found online. Confirm it before using it as a test.
- The forms themselves are not in git. Downloaded copies go in
  `samples/implementation/` (git-ignored, like all samples), with where each came from.
- These file in `3 Implementation` (`filing_model.stage_folders`). None are
  document types yet.
