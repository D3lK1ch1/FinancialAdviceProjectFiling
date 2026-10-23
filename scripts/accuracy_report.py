"""Score the tool on the public samples against their right answers.

    python scripts/accuracy_report.py

Reads the cached answers in samples/.results/ (written by build_public_set.py;
delete a file there to make it be read again) and the right answers in
docs/reference/public_sample_labels.json. Prints the score, the score per type,
why each miss happened, and the number that matters most for automatic
filing: documents that were wrong but would have filed themselves.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "samples" / ".results"
LABELS = ROOT / "docs" / "reference" / "public_sample_labels.json"
NOT_A_TYPE_YET = {"implementation_form"}


def score(results: dict[str, dict], labels: dict[str, str]) -> dict:
    """{"known": [...rows], "not_yet": [...rows]} with one row per labelled document."""
    rows = {"known": [], "not_yet": []}
    for name, want in sorted(labels.items()):
        result = results.get(Path(name).stem)
        if result is None:
            continue
        got = (result.get("classification") or {}).get("doc_type")
        review = result.get("review") or {}
        held = bool(review.get("needs_review"))
        reasons = [r.get("code") for r in review.get("reasons") or []]
        row = {
            "name": name, "want": want, "got": got, "held": held,
            "confidence": (result.get("classification") or {}).get("confidence") or 0.0,
            "right": got == want,
            # The dangerous case: wrong, yet nothing held it for a person.
            "wrong_and_unheld": got not in (None, want) and not held,
            "why": reasons[0] if reasons else ("lookalike" if got not in (None, want) else "none"),
        }
        rows["not_yet" if want in NOT_A_TYPE_YET else "known"].append(row)
    return rows


def main() -> None:
    labels = json.loads(LABELS.read_text())["labels"]
    results = {p.stem: json.loads(p.read_text()) for p in CACHE.glob("*.json")}
    rows = score(results, labels)
    known = rows["known"]
    right = sum(r["right"] for r in known)
    print(f"Known document types: {right} of {len(known)} right ({right / max(len(known), 1):.0%})")
    print(f"Wrong and NOT held (would file itself wrongly): "
          f"{sum(r['wrong_and_unheld'] for r in known + rows['not_yet'])}  <- must be 0")
    print(f"Right but held anyway: {sum(r['right'] and r['held'] for r in known)}")
    by_type = defaultdict(lambda: [0, 0])
    for r in known:
        by_type[r["want"]][0] += r["right"]
        by_type[r["want"]][1] += 1
    print("\nBy type:")
    for t, (ok, n) in sorted(by_type.items()):
        print(f"  {t:<14} {ok} of {n}")
    print("\nWhy the misses happened:")
    for why, n in Counter(r["why"] for r in known if not r["right"]).most_common():
        print(f"  {why:<22} {n}")
    nots = rows["not_yet"]
    print(f"\nNot a document type yet ({len(nots)} implementation forms, #74): "
          f"{sum(r['held'] for r in nots)} held, {sum(r['wrong_and_unheld'] for r in nots)} wrong and not held")
    for r in known + nots:
        if not r["right"]:
            print(f"  miss: {r['name'][:44]:<44} want {r['want']:<20} got {str(r['got']):<13} "
                  f"{r['confidence']:.2f} {'held' if r['held'] else 'NOT HELD'} ({r['why']})")
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
