"""Build activity items from a word list with the engine - the offline assistant.

For every word the engine generates the requested form (the answer) and a few
real forms of the same word that a student might confuse with it (the wrong
options). Ambiguous words and words the engine cannot handle are skipped with a
reason rather than guessed; the teacher reviews every item before use.
"""

from __future__ import annotations

import unicodedata

from arabmorph import Case, Number, Source, Status, generate

STATES = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}
MAX_WORDS = 200
MAX_DISTRACTORS = 3
TRUSTED = 0.85  # forms below this confidence are flagged for the teacher
# Every seed entry carries this warning; the teacher's approval is the review here.
UNREVIEWED = "has not been reviewed by a specialist"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _distractors(word: str, number: Number, case: Case, state: str, exclude: set[str]) -> list[str]:
    """Other cases and states of the same number first, then the same case in the other numbers."""
    definite, construct = STATES[state]
    plan = [(number, c, definite, construct) for c in Case if c is not case]
    plan += [(number, case, d, k) for s, (d, k) in STATES.items() if s != state]
    plan += [(n, case, definite, construct) for n in Number if n is not number]
    out: list[str] = []
    for n, c, d, k in plan:
        r = generate(word, n, c, definite=d, construct=k)
        if r.status is not Status.OK:
            continue
        for f in r.forms:
            v = _nfc(f.vocalized)
            if v not in exclude and v not in out:
                out.append(v)
        if len(out) >= MAX_DISTRACTORS:
            break
    return out[:MAX_DISTRACTORS]


def build_items(words: list[str], number: Number, case: Case, state: str) -> dict:
    definite, construct = STATES[state]
    items, skipped, seen = [], [], set()
    for raw in words:
        word = raw.strip()
        if not word or word in seen:
            continue
        seen.add(word)
        r = generate(word, number, case, definite=definite, construct=construct)
        if r.status is Status.ERROR:
            skipped.append({"word": word, "reason": "error", "detail": r.errors[0] if r.errors else ""})
            continue
        answers = list(dict.fromkeys(_nfc(f.vocalized) for f in r.forms))
        if r.status is Status.AMBIGUOUS:
            skipped.append({"word": word, "reason": "ambiguous", "detail": " / ".join(answers)})
            continue
        warnings = [w for w in (*r.warnings, *(w for f in r.forms for w in f.warnings)) if UNREVIEWED not in w]
        items.append({
            "prompt": word,
            "answer": " / ".join(answers),
            "options": _distractors(word, number, case, state, set(answers)),
            "uncertain": any(f.confidence < TRUSTED or f.source in (Source.HEURISTIC, Source.ASSERTED)
                             for f in r.forms),
            "warnings": list(dict.fromkeys(warnings)),
        })
    return {"items": items, "skipped": skipped}
