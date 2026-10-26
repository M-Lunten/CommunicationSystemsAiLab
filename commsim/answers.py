"""check_answer: instant feedback on the short, objective questions in the lab notebooks.

The expected answers are stored as salted hashes, so they cannot simply be read here.
"""
import hashlib
import json
from pathlib import Path

_KEYS = Path(__file__).with_name("answer_keys.json")


def normalise(answer, decimals=None):
    """Turn an answer into the canonical text that is hashed."""
    if isinstance(answer, dict):
        return ",".join(normalise(answer[k], decimals) for k in sorted(answer))
    if isinstance(answer, (list, tuple)):
        return ",".join(normalise(a, decimals) for a in answer)
    if answer is None:
        return "-"
    if isinstance(answer, bool):
        return "yes" if answer else "no"
    if decimals is not None:
        try:
            return f"{round(float(answer), decimals):.{decimals}f}"
        except (TypeError, ValueError):
            pass
    text = " ".join(str(answer).strip().lower().replace("_", " ").replace("-", " ").split())
    if text in ("", "\u2013", "\u2014"):
        return "-"
    return text.replace(" + ", "+").replace(" +", "+").replace("+ ", "+")


def answer_hash(question, canonical):
    return hashlib.sha256(f"commsim:{question}:{canonical}".encode()).hexdigest()[:20]


def check_answer(question, answer=...):
    """Check your answer to a lab question, e.g. check_answer("A1", 5)."""
    keys = json.loads(_KEYS.read_text()) if _KEYS.exists() else {}
    if question not in keys:
        print(f"There is no automatic check for question {question!r}.")
        return None
    if answer is ...:
        print(f"{question}: write your answer in the call, e.g. check_answer({question!r}, ...)")
        return None
    key = keys[question]
    ok = answer_hash(question, normalise(answer, key.get("decimals"))) in key["hashes"]
    print(f"{question}: {'correct' if ok else 'not correct, think again'}"
          + ("" if ok or not key.get("format") else f"  (answer format: {key['format']})"))
    return ok
