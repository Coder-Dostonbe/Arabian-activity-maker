"""Check items drafted by Claude against the engine.

An item is a prompt (the word) and an answer (a form of it). The engine works
out which form the answer is meant to be and regenerates it:

- engine_agrees: the answer is a form the engine produces from the prompt;
- engine_disagrees: the answer is meant as a form of the prompt (same word,
  or same kind of ending), but the engine writes that form differently; the
  engine's forms are returned so both can be shown;
- not_checkable: the answer is not one Arabic word, or the engine cannot tell
  which form was meant.

A prompt that is a question (ما مثنى «كتاب»؟) agrees if one of its Arabic words
explains the answer; disagreement is only reported for a one-word prompt, where
the word asked about is certain.

Disagreement is reported, never corrected: the teacher decides.
"""

from __future__ import annotations

import re
import unicodedata

from arabmorph import Case, Number, analyze, generate, strip_diacritics
from arabmorph.chars import is_arabic_letter
from arabmorph.noun_input import InputError, parse_noun
from arabmorph.pipeline import default_lexicon

MAX_ITEMS = 200
MAX_TEXT = 300
STATES = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _word(text: str) -> str | None:
    """`text` as one Arabic word, or None (a question, a phrase, Latin text)."""
    text = _nfc(text.strip())
    if not text or any(ch.isspace() for ch in text):
        return None
    return text if all(is_arabic_letter(c) for c in strip_diacritics(text)) else None


def _guessed_numbers(answer: str, singular: str) -> list[Number]:
    """Which number an answer that the engine cannot derive was probably meant to be, from its ending."""
    bare = strip_diacritics(answer)
    if bare.startswith("ال"):
        bare = bare[2:]
    if bare.endswith("ان"):
        return [Number.DUAL]
    if bare.endswith("ين"):
        return [Number.DUAL, Number.PLURAL]
    if bare.endswith(("ون", "ات")):
        return [Number.PLURAL]
    if bare != strip_diacritics(singular) and any(e.plurals for e in default_lexicon().lookup(singular)):
        return [Number.PLURAL]
    return []


def _engine_forms(singular: str, numbers, state: str, cases=tuple(Case)) -> list[str]:
    definite, construct = STATES[state]
    out = []
    for number in numbers:
        for case in cases:
            r = generate(singular, number, case, definite=definite, construct=construct)
            out += [_nfc(f.vocalized) for f in r.forms]
    return list(dict.fromkeys(out))


_ARABIC_WORD = re.compile(r"[ء-يٱ][ء-ْٰٱ]*")


def verify_item(prompt: str, answer: str) -> dict:
    p, a = _word(prompt), _word(answer)
    if a is None:
        return {"status": "not_checkable", "engine": [], "detail": "the answer is not a single Arabic word"}
    if p is None:
        for token in dict.fromkeys(_ARABIC_WORD.findall(_nfc(prompt))):
            result = _check(token, a)
            if result["status"] == "engine_agrees":
                return result
        return {"status": "not_checkable", "engine": [], "detail": "the word asked about is not certain"}
    return _check(p, a)


def _check(p: str, a: str) -> dict:
    try:
        singular = strip_diacritics("".join(c.base for c in parse_noun(p).stem))
    except InputError as exc:
        return {"status": "not_checkable", "engine": [], "detail": str(exc)}

    def same_word(analyses):
        return [x for x in analyses if strip_diacritics(x.singular) == singular]

    agreed = same_word(analyze(a).analyses)
    if agreed:
        x = agreed[0]
        return {"status": "engine_agrees", "engine": [_nfc(x.vocalized)],
                "detail": f"{x.number.value}, {x.state}, {'/'.join(c.value for c in x.cases)}"}

    # Right word and form, wrong vowels: the bare spelling analyses back to the prompt.
    by_spelling = same_word(analyze(strip_diacritics(a)).analyses)
    if by_spelling:
        forms = []
        for x in by_spelling:
            forms += _engine_forms(singular, [x.number], x.state, x.cases)
        return {"status": "engine_disagrees", "engine": list(dict.fromkeys(forms)),
                "detail": "the vowels differ from the engine's"}

    state = "definite" if strip_diacritics(a).startswith("ال") else "indefinite"
    numbers = _guessed_numbers(a, singular)
    forms = _engine_forms(singular, numbers, state) if numbers else []
    if forms:
        return {"status": "engine_disagrees", "engine": forms,
                "detail": f"the engine's {'/'.join(n.value for n in numbers)} forms differ"}
    return {"status": "not_checkable", "engine": [], "detail": "the engine cannot tell which form is meant"}


def verify_items(items: list[dict]) -> list[dict]:
    return [verify_item(i.get("prompt", ""), i.get("answer", "")) for i in items]
