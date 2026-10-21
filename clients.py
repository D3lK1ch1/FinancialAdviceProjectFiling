import re

from kb import KB as _KB

_NAME_LABELS = _KB["client_model"]["name_labels"]
_NAME_FORMAT = _KB["client_model"]["name_format"]
_TITLES = {title.lower(): title for title in _NAME_FORMAT["titles"]}
_PARTICLES = {particle.lower() for particle in _NAME_FORMAT["surname_particles"]}
_ENTITY = _KB["client_model"]["entity_client"]
_ENTITY_MARKERS = {marker.lower(): marker for marker in _ENTITY["markers"]}
_TRUSTEE_WORDS = {marker.lower() for marker in _ENTITY["trustee_markers"] if " " not in marker}
# "as trustee for" is three words; the finder reads it as one, ATF.
_TRUSTEE_PHRASES = re.compile(
    r"\b(" + "|".join(r"\s+".join(map(re.escape, m.split())) for m in _ENTITY["trustee_markers"] if " " in m) + r")\b",
    re.IGNORECASE,
)

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
# The same, for a name the document writes in capitals ("JOHN SMITH").
_CAPS_WORD = re.compile(r"^[A-Z][A-Z'’-]*[A-Z]$")
_JOINERS = {"and", "&"}
_TOKEN = re.compile(r"(\s*)(\S+)")
_COLUMN_GAP = 3
_FIELD_LOOKAHEAD = 3
_MAX_TOKENS = 8

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
    text = _TRUSTEE_PHRASES.sub("ATF", text)
    tokens = [(m.group(1), m.group(2)) for m in _TOKEN.finditer(text)][:_MAX_TOKENS]
    words = [word for _, word in tokens]
    name = []
    in_capitals = None
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
        lower = word.lower()
        # A name keeps the style it starts in. "JOHN SMITH" is a name in
        # capitals; in "Nick Rossi AFS licensees" the capitals are the next
        # column. Entity words ("Pty Ltd", "SMSF", "ATF") belong in either.
        if in_capitals is None and (_NAME_WORD.match(word) or _CAPS_WORD.match(word)):
            in_capitals = bool(_CAPS_WORD.match(word))
        if lower in _ENTITY_MARKERS or lower in _TRUSTEE_WORDS:
            if not name:
                break
            name.append(word)
        elif (_CAPS_WORD if in_capitals else _NAME_WORD).match(word):
            name.append(word)
        elif name and (lower in _JOINERS or lower in _PARTICLES):
            # "Brad and Zara Black", "Anna van der Berg": kept only if a name
            # word follows, which the trailing trim below checks.
            name.append(word)
        else:
            break
    while name and (name[-1].lower() in _JOINERS or name[-1].lower() in _PARTICLES
                    or name[-1].lower() in _TRUSTEE_WORDS):
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
            # The name as read may differ from the text ("as trustee for" is read as ATF).
            at = after.find(name)
            after = (after[at + len(name):] if at >= 0 else after)[:_CONTEXT_CHARS]
            candidates.append({
                "raw": name,
                "label": _collapse(match.group(1)).lower(),
                "page": page_number,
                "context": _collapse(f"{before} {_collapse(match.group())} {name}{after}"),
            })
    return candidates


# --- Folder name (#6) -------------------------------------------------------
#
# What a found name becomes as a client folder, by the rules Bella decided
# (client_model.name_format and joint_client): surname first, normal capitals
# whatever the document uses, titles kept, a joint client in one folder.
#
#     "JOHN SMITH"           -> "Smith, John"
#     "Dr John Smith"        -> "Smith, Dr John"
#     "Anna van der Berg"    -> "van der Berg, Anna"
#     "Brad and Zara Black"  -> "Black, Brad & Zara"
#
# A name that can't be read safely gives no folder and a reason. A folder name
# is the filing key, and a wrong one files a document under another client.


def _recapitalise(word: str) -> str:
    # Only words the document wrote in capitals. "McDonald" and "O'Brien" are
    # already right; "MCDONALD" comes back "Mcdonald", which nothing can fix
    # without knowing the name.
    if not word.isupper():
        return word
    return re.sub(r"[A-Za-z]+", lambda m: m.group().capitalize(), word)


def _person(words: list[str]) -> dict:
    """Titles, given names and surname of one person's words, in order."""
    titles = []
    while words and words[0].lower().rstrip(".") in _TITLES:
        titles.append(_TITLES[words[0].lower().rstrip(".")])
        words = words[1:]
    surname_start = len(words) - 1
    while surname_start > 0 and words[surname_start - 1].lower() in _PARTICLES:
        surname_start -= 1
    surname = [w.lower() if i < len(words) - 1 else _recapitalise(w)
               for i, w in enumerate(words[surname_start:], start=surname_start)]
    return {
        "titles": titles,
        "given": [_recapitalise(w) for w in words[:surname_start]],
        "surname": " ".join(surname),
    }


# Short words an all-capitals entity name writes the same way as an acronym.
_ENTITY_SMALL_WORDS = {"the", "of", "and", "for"}


def _entity_word(word: str) -> str:
    lower = word.lower()
    if lower in _ENTITY_MARKERS:
        return _ENTITY_MARKERS[lower]
    # "SMITH" in "SMITH FAMILY TRUST" is a word in capitals; "ABC" in "ABC Pty
    # Ltd" is probably an acronym. Three letters or fewer stays as written.
    if word.isupper() and (len(word) > 3 or lower in _ENTITY_SMALL_WORDS):
        return _recapitalise(word)
    return word


def party_type(raw: str) -> str:
    """individual, joint or entity (client_model.entity_client)."""
    words = [w.lower() for w in raw.split()]
    if any(w in _ENTITY_MARKERS or w in _TRUSTEE_WORDS for w in words):
        return "entity"
    if any(w in _JOINERS for w in words):
        return "joint"
    return "individual"


def client_folder_name(raw: str) -> dict:
    """{"folder": name or None, "party_type": ..., "reason": why not, or None}."""
    kind = party_type(raw)
    result = _folder_for(raw, kind)
    return {"folder": result["folder"], "party_type": kind, "reason": result["reason"]}


def _folder_for(raw: str, kind: str) -> dict:
    if kind == "entity":
        words = raw.split()
        # "John Smith ATF Smith Family Trust": the client is the trust.
        trustee_at = [i for i, w in enumerate(words) if w.lower() in _TRUSTEE_WORDS]
        if trustee_at:
            words = words[trustee_at[-1] + 1:]
        if not words or not any(w.lower() in _ENTITY_MARKERS for w in words):
            return {"folder": None, "reason": f"{raw!r} names a trustee but no trust or company"}
        # The entity's own name, in normal capitals (entity_client): no
        # surname-first reordering, which is only for people.
        return {"folder": " ".join(_entity_word(w) for w in words), "reason": None}
    return _person_folder(raw)


def _person_folder(raw: str) -> dict:
    parts, current = [], []
    for word in raw.split():
        if word.lower() in _JOINERS:
            parts.append(current)
            current = []
        else:
            current.append(word)
    parts.append(current)

    if any(not part for part in parts) or len(parts) > 2:
        return {"folder": None, "reason": f"can't read {raw!r} as one or two people"}

    people = [_person(part) for part in parts]
    last = people[-1]
    if not last["given"]:
        return {"folder": None, "reason": f"{raw!r} has no first name, so the surname can't be told apart"}

    if len(people) == 1:
        return {"folder": f"{last['surname']}, {' '.join(last['titles'] + last['given'])}", "reason": None}

    # Joint: "Brad and Zara Black" names the surname once, at the end. In
    # "Brad Black and Zara Black" both carry it, and it must be the same.
    first = people[0]
    if first["given"] and first["surname"].lower() != last["surname"].lower():
        return {
            "folder": None,
            "reason": "a joint client with two different surnames; how to name its folder isn't decided (#61)",
        }
    first_names = first["titles"] + first["given"] + ([] if first["given"] else [first["surname"]])
    # Document order, not husband first (joint_client.order): nothing in the
    # name says which is which, and guessing would be wrong half the time.
    second_names = last["titles"] + last["given"]
    return {"folder": f"{last['surname']}, {' '.join(first_names)} & {' '.join(second_names)}", "reason": None}


# --- Choosing the client (#6) ----------------------------------------------
#
# A document names its client in several places (a header on every page, a
# "Client name:" field). choose_client() reads every name found as a folder
# and proposes one only when they all agree. It never chooses between
# different clients: a document in the wrong client's folder is the worst
# failure this tool can make, so two different answers go to the adviser
# as the ambiguous_client flag (client_model.several_names).


def _words(raw: str) -> set[str]:
    return {w.lower() for w in raw.split() if w.lower() not in _JOINERS}


def choose_client(candidates: list[dict]) -> dict:
    """{"folder", "party_type", "reason", "ambiguous", "names"}.

    `names` is every distinct folder read from the document, so a reviewer
    sees what was found even when nothing is proposed.
    """
    readable, unreadable = {}, []
    for candidate in candidates:
        read = client_folder_name(candidate["raw"])
        if read["folder"] is None:
            unreadable.append((candidate["raw"], read["reason"]))
        else:
            readable.setdefault(read["folder"].lower(), read)
    names = [read["folder"] for read in readable.values()]

    if not candidates:
        return {"folder": None, "party_type": None, "ambiguous": False, "names": [],
                "reason": "the document labels no client; a person chooses one"}
    if not readable:
        return {"folder": None, "party_type": None, "ambiguous": False, "names": [],
                "reason": unreadable[0][1]}
    if len(readable) > 1:
        return {"folder": None, "party_type": None, "ambiguous": True, "names": names,
                "reason": f"the document names more than one client ({'; '.join(names)}); the adviser chooses"}

    [chosen] = readable.values()
    chosen_raw_words = set().union(*(_words(c["raw"]) for c in candidates
                                     if client_folder_name(c["raw"])["folder"] == chosen["folder"]))
    # "Smith" next to "John Smith" is the same client said more briefly. A
    # name that is NOT part of the chosen one may be someone else.
    strangers = [raw for raw, _ in unreadable if not _words(raw) <= chosen_raw_words]
    if strangers:
        return {"folder": None, "party_type": None, "ambiguous": True, "names": names + strangers,
                "reason": f"the document also names {', '.join(map(repr, strangers))}; the adviser chooses"}
    return {"folder": chosen["folder"], "party_type": chosen["party_type"], "ambiguous": False,
            "names": names, "reason": None}
