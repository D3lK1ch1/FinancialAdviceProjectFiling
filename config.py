"""Machine settings, read from environment variables (#7).

What differs between one machine and the next: where Ollama listens, which
model it serves, how long to wait. Document rules never go here; they live in
knowledge_base.json (ground rule #1). Every default is the value this project
has always run with, so an unset variable changes nothing.

Kept out of classifier.py on purpose. tests/test_storage.py forbids `os` in
classification code as its marker for file-system access (ground rule #3).
Environment variables aren't storage, but loosening that guard for them would
also let a path in. This module reads settings and knows no paths.
"""

import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
# The same server's root, for asking it which model and version it is running.
OLLAMA_BASE_URL = OLLAMA_URL.rsplit("/api/", 1)[0]
# A different model is a different classifier. Change it only deliberately,
# and re-run the samples when you do.
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_TIMEOUT_SECONDS = float(os.environ.get("OLLAMA_TIMEOUT", "180"))

# demo (the default): no uploads at all; the screens show built-in sample sets
# only. live: a firm's own installation, set up on purpose, where its documents
# may be read. Anything other than "live" is demo, so a typo stays safe.
APP_MODE = "live" if os.environ.get("APP_MODE", "demo").strip().lower() == "live" else "demo"
