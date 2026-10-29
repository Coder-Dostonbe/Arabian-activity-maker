"""Build activity items from a word list with the engine - the offline assistant.

For every word the engine generates the requested form (the answer) and a few
real forms of the same word that a student might confuse with it (the wrong
options). Ambiguous words and words the engine cannot handle are skipped with a
reason rather than guessed; the teacher reviews every item before use.
"""

from __future__ import annotations

import unicodedata

from arabmorph import Case, Lexicon, Number, PluralKind, Source, Status, generate
from arabmorph.chars import (ALEF, ALEF_MAQSURA, DAMMA, DAMMATAN, FATHA, FATHATAN, KASRA, KASRATAN,
                             SUKUN, YEH)
from arabmorph.clusters import Cluster, join_clusters, split_clusters
from arabmorph.noun_input import InputError, parse_noun
from arabmorph.orthography import add_article

STATES = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}
MAX_WORDS = 200
MAX_DISTRACTORS = 3
TRUSTED = 0.85  # forms below this confidence are flagged for the teacher
# Every seed entry carries this warning; the teacher's approval is the review here.
UNREVIEWED = "has not been reviewed by a specialist"


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# Suffixes glued on with none of the stem changes the rules require: (nominative, accusative/genitive).
NAIVE_DUAL = {False: (FATHA + "انِ", FATHA + YEH + SUKUN + "نِ"), True: (FATHA + "ا", FATHA + YEH + SUKUN)}
SHORT = (DAMMA, FATHA, KASRA)
TANWEEN = (DAMMATAN, FATHATAN, KASRATAN)


def _real_forms(word: str, number: Number, state: str) -> set[str]:
    """Every correct form of `word` in `number` and `state`, in any case: a rule-error distractor is none of them."""
    definite, construct = STATES[state]
    return {_nfc(f.vocalized) for c in Case
            for f in generate(word, number, c, definite=definite, construct=construct).forms}


def _naive_dual(word: str, case: Case, state: str) -> list[str]:
    """صحراءان، مستشفاان: the dual suffix added to the unchanged singular."""
    r = generate(word, Number.SINGULAR, Case.NOMINATIVE)
    if r.status is not Status.OK:
        return []
    try:
        stem = list(parse_noun(r.forms[0].vocalized).stem)
    except InputError:
        return []
    # The indefinite singular may carry tanween before a maqsur alif (مُسْتَشْفًى); the naive form keeps the vowel only.
    stem = [c.without(set(TANWEEN)).with_marks(c.without(set(TANWEEN)).marks + SHORT[TANWEEN.index(t)])
            if (t := next((m for m in TANWEEN if c.has(m)), None)) else c for c in stem]
    if stem[-1].base == ALEF_MAQSURA:
        stem[-1] = Cluster(ALEF)
    definite, construct = STATES[state]
    suffix = NAIVE_DUAL[construct][0 if case is Case.NOMINATIVE else 1]
    vowel, rest = suffix[0], suffix[1:]
    last = stem[-1].without_case_marks()
    # The vowel before the suffix sits on the stem's last letter (none on an alif).
    last = last if last.base == ALEF else last.with_marks(last.marks + vowel)
    clusters = split_clusters(join_clusters(stem[:-1] + [last]) + rest)
    return [_nfc(join_clusters(add_article(clusters) if definite else clusters))]


def _sound_instead_of_broken(word: str, case: Case, state: str, answers_kinds: set) -> list[str]:
    """كتابات / كتابون for a noun whose plural is broken: the sound plural applied by analogy."""
    if answers_kinds != {PluralKind.BROKEN}:
        return []
    lemma = generate(word, Number.SINGULAR, Case.NOMINATIVE)
    if lemma.status is not Status.OK:
        return []
    bare_lemma = _nfc(lemma.forms[0].vocalized)
    definite, construct = STATES[state]
    out = []
    for kind in (PluralKind.SOUND_FEMININE, PluralKind.SOUND_MASCULINE):
        r = generate(bare_lemma, Number.PLURAL, case, definite=definite, construct=construct, kind=kind,
                     lexicon=Lexicon.empty())
        out += [_nfc(f.vocalized) for f in r.forms] if r.status is not Status.ERROR else []
    return out


def _wrong_suffix(answer: str, real: set[str]) -> list[str]:
    """The answer with its case vowel swapped for one no case uses (مُعَلِّمَاتًا، مَدَارِسٍ)."""
    clusters = split_clusters(answer)
    for i in range(len(clusters) - 1, max(len(clusters) - 3, -1), -1):
        c = clusters[i]
        group = next((g for g in (TANWEEN, SHORT) if any(c.has(m) for m in g)), None)
        if group is None:
            continue
        current = next(m for m in group if c.has(m))
        for other in group:
            if other == current:
                continue
            swapped = clusters[:i] + [c.without({current}).with_marks(c.without({current}).marks + other)] + clusters[i + 1:]
            candidate = _nfc(join_clusters(swapped))
            if candidate not in real:
                return [candidate]
        return []
    return []


def _rule_errors(word: str, number: Number, case: Case, state: str, answers: list[str], kinds: set) -> list[str]:
    """Forms a student gets by misapplying a rule; never a correct form of the word in this number and state."""
    real = _real_forms(word, number, state)
    out = []
    if number is Number.PLURAL:
        out += _sound_instead_of_broken(word, case, state, kinds)
    if number is Number.DUAL:
        out += _naive_dual(word, case, state)
    for a in answers:
        out += _wrong_suffix(a, real)
    return [o for o in dict.fromkeys(out) if o not in real]


def _distractors(word: str, number: Number, case: Case, state: str, exclude: set[str],
                 kinds: set = frozenset()) -> list[str]:
    """One other case or state of the same form first (the classic confusion), then rule errors,
    then the remaining cases and states, then the same case in the other numbers."""
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
    errors = [e for e in _rule_errors(word, number, case, state, sorted(exclude), kinds) if e not in exclude]
    ordered = out[:1] + errors + out[1:]
    return list(dict.fromkeys(o for o in ordered if o not in exclude))[:MAX_DISTRACTORS]


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
            "options": _distractors(word, number, case, state, set(answers), {f.kind for f in r.forms}),
            "rules": list(dict.fromkeys(rid for f in r.forms for rid in f.rule_ids)),
            "uncertain": any(f.confidence < TRUSTED or f.source in (Source.HEURISTIC, Source.ASSERTED)
                             for f in r.forms),
            "warnings": list(dict.fromkeys(warnings)),
        })
    return {"items": items, "skipped": skipped}
