import json
import re

with open("knowledge_base.json") as f:
    _KB = json.load(f)

_NAME_LABELS = _KB["client_model"]["name_labels"]

# Matched against the page text as extracted, not whitespace-collapsed: the
# gaps layout extraction leaves between columns are evidence of where a name
# ends (see _name_after).
_LABEL = re.compile(
    r"\b(" + "|".join(r"\s+".join(map(re.escape, label.split())) for label in _NAME_LABELS) + r")\b\s*:?",
    re.IGNORECASE,
)

# A name word starts with a capital and has a lower-case letter in it, so an
# all-capitals token from a neighbouring column ("AFS", "ABC") ends the name.
_NAME_WORD = re.compile(r"^[A-Z][A-Za-z'’-]*[a-z][A-Za-z'’-]*$")
_JOINERS = {"and", "&"}
_TOKEN = re.compile(r"(\s*)(\S+)")
_COLUMN_GAP = 3
_FIELD_LOOKAHEAD = 3
_MAX_TOKENS = 6

_CONTEXT_CHARS = 40


def _is_gap(whitespace: str) -> bool:
    return "\n" in whitespace or len(whitespace) >= _COLUMN_GAP


def _starts_new_field(words: list[str], i: int) -> bool:
    # "George Baker Date of advice: ..." / "Wendy Zhang Account number: ..." —
    # a field label is one capitalised word, then only lower-case words, the
    # last ending in a colon. The word that opens one is not part of the name.
    for j in range(i, min(i + _FIELD_LOOKAHEAD, len(words))):
        if j > i and not words[j][:1].islower():
            return False
        if words[j].endswith(":"):
            return True
    return False


def _name_after(text: str) -> str | None:
    tokens = [(m.group(1), m.group(2)) for m in _TOKEN.finditer(text)][:_MAX_TOKENS]
    words = [word for _, word in tokens]
    name = []
    for i, (gap, word) in enumerate(tokens):
        name_words = [w for w in name if w.lower() not in _JOINERS]
        # Layout extraction puts the next column's text on the same line
        # ("John Patel      The SOA must include"), but also spreads a
        # single name across a gap ("Wendy        Zhang"). So a gap ends the
        # name only once it has a first and a last name.
        if len(name_words) >= 2 and _is_gap(gap):
            break
        if _starts_new_field(words, i):
            break
        if _NAME_WORD.match(word):
            name.append(word)
        elif word.lower() in _JOINERS and name:
            name.append(word)
        else:
            break
    while name and name[-1].lower() in _JOINERS:
        name.pop()
    return " ".join(name) or None


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_client_candidates(pages: list[str]) -> list[dict]:
    candidates = []
    for page_number, page_text in enumerate(pages, start=1):
        for match in _LABEL.finditer(page_text):
            name = _name_after(page_text[match.end():])
            if name is None:
                continue
            before = _collapse(page_text[:match.start()])[-_CONTEXT_CHARS:]
            after = _collapse(page_text[match.end():])
            after = after[after.find(name) + len(name):][:_CONTEXT_CHARS]
            candidates.append({
                "raw": name,
                "label": _collapse(match.group(1)).lower(),
                "page": page_number,
                "context": _collapse(f"{before} {_collapse(match.group())} {name}{after}"),
            })
    return candidates
