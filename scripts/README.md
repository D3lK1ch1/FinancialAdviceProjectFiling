# Scripts

## Test the tool on the public samples

From the project folder, with the environment active and Ollama running:

    python scripts/build_public_set.py
    python scripts/accuracy_report.py

The first reads every PDF under `samples/` that it hasn't read before (about a
minute each) and caches each answer. The second prints the score.

- **After changing the knowledge base or the code,** delete `samples/.results/` first,
  so every document is read again with the change. Otherwise old answers are reused.
- **To use the intended model**, Llama 3.1, nothing extra is needed: it is the default.
  To try another, set `OLLAMA_MODEL`, for example `OLLAMA_MODEL=qwen3:8b`.

## Where the samples are

All in `samples/` (git-ignored: public documents, but not ours to redistribute).

| Folder | What | Where they came from |
|---|---|---|
| `samples/public/` | ASIC example SOAs and ROAs, blank fact finds and risk profiles, UniSuper PDSs | `samples/public/SOURCES.md` |
| `samples/implementation/<kind>/` | Blank provider forms, one folder per kind (#74) | `samples/implementation/SOURCES.md` |
| `samples/.results/` | The tool's cached answer for each file | written by `build_public_set.py` |

The right answer for each file is in `docs/reference/public_sample_labels.json`. Add a
line there for every new sample, or the report leaves it out.

## Adding samples

Public documents only: published examples, blank templates, provider forms. Never a
firm's client files. Put each in the matching folder, add its source to that folder's
`SOURCES.md` and its right answer to the labels file. New samples are a fresh test:
score them before changing anything because of them.
