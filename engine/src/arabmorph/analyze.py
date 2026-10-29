"""Reverse analysis: which singular, number, case and state could a written form be?

Candidates come from the lexicon's broken plurals and from stripping the sound
suffixes (ـان ـين ـون ـات, and ـا ـي ـو of the construct state). Every
candidate is then confirmed by generating it again: an analysis is reported
only if the engine itself produces exactly the input from that singular, so
the analysis can never disagree with generation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chars import VOCALIZATION_MARKS
from .clusters import bare, split_clusters
from .generate import generate
from .lexicon import Lexicon
from .noun_input import InputError, parse_noun
from .normalize import fold_input, strip_diacritics
from .pipeline import _reject, _resolve_final_yeh, _singular_candidates, default_lexicon
from .types import Case, GeneratedForm, Number, PluralKind, Source, Status

# The construct state drops the ن of the dual and sound masculine plural: كتابا، كتابي، مهندسو.
CONSTRUCT_ENDINGS = {"ا": "ان", "ي": "ين", "و": "ون"}
STATES = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}


@dataclass(frozen=True)
class Analysis:
    singular: str                 # vocalised lemma when the lexicon has it, else the bare spelling
    number: Number
    state: str                    # indefinite / definite / construct
    cases: tuple[Case, ...]       # every case whose form is written like the input
    kind: PluralKind | None
    vocalized: str                # the regenerated form, fully vocalised where known
    entry_id: str | None          # None when the lexicon has no entry, or several homographs
    in_lexicon: bool
    rule_ids: tuple[str, ...]
    source: Source
    confidence: float
    condition: str | None = None

    def to_dict(self) -> dict:
        return {
            "singular": self.singular,
            "number": self.number.value,
            "state": self.state,
            "cases": [c.value for c in self.cases],
            "kind": self.kind.value if self.kind else None,
            "vocalized": self.vocalized,
            "entry_id": self.entry_id,
            "in_lexicon": self.in_lexicon,
            "rules": list(self.rule_ids),
            "source": self.source.value,
            "confidence": self.confidence,
            "condition": self.condition,
        }


@dataclass(frozen=True)
class AnalysisResult:
    input: str
    status: Status
    analyses: tuple[Analysis, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "input": self.input,
            "status": self.status.value,
            "analyses": [a.to_dict() for a in self.analyses],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "suggestions": list(self.suggestions),
        }


def analyze(word: str, *, lexicon: Lexicon | None = None) -> AnalysisResult:
    """Candidate singulars of `word` with number, case, state and plural kind.

    The status is ok only when one lexicon lemma, number and kind explain the
    input (the case and state often cannot be told apart in writing); several
    lemmas or numbers, or a singular missing from the lexicon, make it ambiguous.
    """
    lexicon = default_lexicon() if lexicon is None else lexicon
    try:
        parsed = parse_noun(word)
    except InputError as exc:
        return AnalysisResult(word, Status.ERROR, errors=(str(exc),))
    parsed = _resolve_final_yeh(parsed, lexicon)
    typed = split_clusters(fold_input(word.strip()).text)
    target = bare(typed)
    key = bare(parsed.stem)
    warnings = [w for w in parsed.warnings if "assumed to be singular" not in w]

    states = ["definite"] if parsed.definite else ["indefinite", "construct"]
    found: dict[tuple, list[tuple[Case, GeneratedForm]]] = {}
    for singular in _candidates(key, parsed.definite, lexicon):
        for number in Number:
            for state in states:
                definite, construct = STATES[state]
                for case in Case:
                    r = generate(singular, number, case, definite=definite, construct=construct, lexicon=lexicon)
                    for f in r.forms:
                        if f.text == target and _vowels_agree(typed, f.vocalized):
                            found.setdefault((singular, number, state, f.kind), []).append((case, f))

    analyses = sorted((_analysis(k, v, lexicon) for k, v in found.items()),
                      key=lambda a: (not a.in_lexicon, -a.confidence))
    if any(a.in_lexicon for a in analyses) and not all(a.in_lexicon for a in analyses):
        # Generation itself refuses a spelling that inflects a lexicon word (كتابين, مستشفيان);
        # a reading from an unknown singular would be the same guess.
        analyses = [a for a in analyses if a.in_lexicon]
        warnings.append("Readings from singulars that are not in the lexicon were left out, "
                        "because a lexicon word explains this form.")
    if not analyses:
        rejected = _reject(parsed, lexicon)
        message, suggestions = rejected if rejected else ("No singular noun produces this form.", [])
        return AnalysisResult(word, Status.ERROR, warnings=tuple(dict.fromkeys(warnings)),
                              errors=(message,), suggestions=tuple(dict.fromkeys(suggestions)))
    readings = {(a.entry_id or a.singular, a.number, a.kind) for a in analyses}
    certain = len(readings) == 1 and all(a.entry_id for a in analyses)
    if any(a.in_lexicon and not a.entry_id for a in analyses):
        warnings.append("The lexicon has several words with this spelling (e.g. different vowels); "
                        "the analysis cannot tell which one is meant.")
    if not all(a.in_lexicon for a in analyses):
        warnings.append("Some analyses use a singular that is not in the lexicon; they rest on spelling alone.")
    return AnalysisResult(word, Status.OK if certain else Status.AMBIGUOUS, tuple(analyses),
                          tuple(dict.fromkeys(warnings)))


def _candidates(key: str, definite: bool, lexicon: Lexicon) -> list[str]:
    """Bare singular spellings worth regenerating; generation decides which are right."""
    found = [key]
    # كتبًا ← كتب (tanween alif); قاضٍ، ليالٍ ← قاضي، ليالي (manqus without its yeh)
    stems = [key, key + "ي"] + ([key[:-1]] if key.endswith("ا") else [])
    found += [e.key for stem in stems for e in lexicon.singulars_of(stem)]
    if lexicon.lookup(key + "ي"):
        found.append(key + "ي")
    found += [s for _, s in _singular_candidates(key)]
    if not definite and len(key) >= 3 and key[-1] in CONSTRUCT_ENDINGS:
        found += [s for _, s in _singular_candidates(key[:-1] + CONSTRUCT_ENDINGS[key[-1]])]
        found.append(key[:-1])    # أبو / أبا / أبي ← أب (الأسماء الخمسة)
    return list(dict.fromkeys(s for s in found if len(s) >= 2))


def _vowels_agree(typed, vocalized: str) -> bool:
    """Every vowel the user typed is in the generated form, wherever that form is vocalised."""
    generated = split_clusters(vocalized)
    if len(generated) != len(typed):
        return False
    for t, g in zip(typed, generated):
        tv = {m for m in t.marks if m in VOCALIZATION_MARKS}
        gv = {m for m in g.marks if m in VOCALIZATION_MARKS}
        if tv and gv and not tv <= gv:
            return False
    return True


def _entries_with_plural(entries, form: GeneratedForm, kind: PluralKind | None):
    """Homographs (مَدْرَسَة / مُدَرِّسَة) told apart by the plural they record."""
    if kind is PluralKind.BROKEN:
        stem = form.text[2:] if form.definite else form.text
        return [e for e in entries if any(p.form and strip_diacritics(p.form) == stem for p in e.plurals)]
    return [e for e in entries if any(p.kind is kind for p in e.plurals)]


def _analysis(key: tuple, hits: list[tuple[Case, GeneratedForm]], lexicon: Lexicon) -> Analysis:
    singular, number, state, kind = key
    best = max((f for _, f in hits), key=lambda f: f.confidence)
    entries = lexicon.lookup(singular)
    if len(entries) > 1 and number is Number.PLURAL:
        entries = _entries_with_plural(entries, best, kind) or entries
    entry = entries[0] if len(entries) == 1 else None
    return Analysis(
        singular=entry.lemma if entry else singular,
        number=number,
        state=state,
        cases=tuple(c for c in Case if any(c is hc for hc, _ in hits)),
        kind=kind,
        vocalized=best.vocalized,
        entry_id=entry.id if entry else None,
        in_lexicon=bool(entries),
        rule_ids=best.rule_ids,
        source=best.source,
        confidence=best.confidence,
        condition=best.condition,
    )
