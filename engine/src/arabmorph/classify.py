"""Classify a noun stem by its final letter.

Returns one or more Interpretations. More than one means the evidence
(spelling, diacritics, lexicon) does not settle the question; callers must
surface that ambiguity rather than pick one silently.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .chars import (
    ALEF,
    ALEF_MAQSURA,
    CASE_MARKS,
    HAMZA,
    KASRA,
    SHADDA,
    SUKUN,
    TEH_MARBUTA,
    YEH,
)
from .clusters import Cluster, bare
from .lexicon import Lexicon, LexiconEntry
from .noun_input import ParsedNoun
from .types import AlifOrigin, FinalClass, HamzaType, Source


@dataclass(frozen=True)
class Interpretation:
    stem: tuple[Cluster, ...]
    final_class: FinalClass
    source: Source
    confidence: float
    alif_origin: AlifOrigin | None = None
    hamza_type: HamzaType | None = None
    condition: str | None = None
    entry_id: str | None = None
    warnings: tuple[str, ...] = ()


def interpret(parsed: ParsedNoun, lexicon: Lexicon) -> tuple[list[Interpretation], list[str]]:
    warnings: list[str] = []
    stem = parsed.stem
    bases = bare(stem)

    hits = _lexicon_hits(stem, lexicon, warnings)
    if hits:
        return hits, warnings

    # Indefinite manqus drops its yeh in the nominative/genitive (قاضٍ).
    if bases[-1] not in (YEH, ALEF, ALEF_MAQSURA):
        restored = stem + (Cluster(YEH),)
        manqus = [h for h in _lexicon_hits(restored, lexicon, warnings) if h.final_class is FinalClass.MANQUS]
        if manqus:
            return [
                replace(h, confidence=h.confidence - 0.05,
                        condition="The final yeh is assumed to have been dropped (indefinite manqus).")
                for h in manqus
            ], warnings
        if parsed.final_kasratan and len(bases) >= 3 and bases[-2] == ALEF:
            warnings.append(
                "If this is a manqus noun whose yeh was dropped (like قاضٍ), the result is wrong; "
                "enter the form with yeh (قاضي) instead."
            )

    if bases[-1] == ALEF:
        return _interpret_final_alif(parsed, lexicon, warnings), warnings
    return _by_spelling(stem), warnings


def _lexicon_hits(stem, lexicon: Lexicon, warnings: list[str]) -> list[Interpretation]:
    entries = lexicon.lookup(bare(stem))
    hits = []
    for e in entries:
        if _compatible(stem, e.clusters):
            hits.append(_from_entry(e))
        else:
            warnings.append(f"Lexicon entry {e.lemma} ({e.id}) was not applied: the input vocalisation differs.")
    if len(hits) > 1:
        by_id = {e.id: e for e in entries}
        hits = [replace(h, condition=f"If the word is {by_id[h.entry_id].lemma} ({by_id[h.entry_id].gloss_en}).")
                for h in hits]
    return hits


def _from_entry(e: LexiconEntry) -> Interpretation:
    return Interpretation(
        stem=tuple(e.clusters),
        final_class=e.final_class,
        source=Source.LEXICON,
        confidence=0.95 if e.verified else 0.9,
        alif_origin=e.alif_origin,
        hamza_type=e.hamza_type,
        entry_id=e.id,
        warnings=() if e.verified else (f"Lexicon entry {e.id} has not been reviewed by a specialist.",),
    )


def _compatible(given, lemma) -> bool:
    """Input marks must be a subset of the lemma's marks (final case marks ignored)."""
    if len(given) != len(lemma):
        return False
    for i, (a, b) in enumerate(zip(given, lemma)):
        if a.base != b.base:
            return False
        marks = set(a.marks) - (CASE_MARKS if i == len(given) - 1 else set())
        if not marks <= set(b.marks):
            return False
    return True


def _interpret_final_alif(parsed: ParsedNoun, lexicon: Lexicon, warnings: list[str]) -> list[Interpretation]:
    stem = parsed.stem
    n = len(stem)
    if n < 3:
        return []
    acc_stem = stem[:-1]
    acc_stem = acc_stem[:-1] + (acc_stem[-1].without_case_marks(),)

    def accusative(confidence: float) -> list[Interpretation]:
        found = _lexicon_hits(acc_stem, lexicon, warnings) or _by_spelling(acc_stem)
        cond = "The final ا is read as the alif of accusative tanween (ـًا)."
        return [replace(i, confidence=round(min(i.confidence, confidence), 2), condition=cond) for i in found]

    if n == 3:
        maqsur = Interpretation(
            stem=stem, final_class=FinalClass.MAQSUR, source=Source.HEURISTIC,
            confidence=0.6, alif_origin=AlifOrigin.WAW,
            condition="Read as a trilateral maqsur noun; an alif written ا usually derives from waw (spelling convention).",
        )
        acc = accusative(0.5 if parsed.tanween_alif else 0.4)
        return [maqsur, *acc]

    if parsed.tanween_alif:
        return accusative(0.9)
    if stem[-2].base == YEH:
        # Maqsur nouns of 4+ letters are written with ا only after yeh (دنيا).
        maqsur = Interpretation(
            stem=stem, final_class=FinalClass.MAQSUR, source=Source.HEURISTIC, confidence=0.5,
            condition="Read as a maqsur noun (alif written ا after yeh, like دنيا).",
        )
        return [maqsur, *accusative(0.5)]
    warnings.append(
        "Loanwords ending in ا (such as سينما) are not covered; for those this result does not apply."
    )
    return accusative(0.7)


def _by_spelling(stem) -> list[Interpretation]:
    n = len(stem)
    last = stem[-1]
    prev = stem[-2] if n >= 2 else None
    b = last.base

    def one(cls, conf, src=Source.RULE, **kw):
        return [Interpretation(stem=stem, final_class=cls, source=src, confidence=conf, **kw)]

    if b == TEH_MARBUTA:
        return one(FinalClass.SOUND, 0.97)
    if b == ALEF_MAQSURA:
        if n >= 4:
            return one(FinalClass.MAQSUR, 0.95)
        if n == 3:
            return one(
                FinalClass.MAQSUR, 0.75, Source.HEURISTIC, alif_origin=AlifOrigin.YEH,
                condition="In a trilateral noun, an alif written ى usually derives from yeh (spelling convention).",
                warnings=("The origin of the alif was inferred from spelling, not from a lexicon entry.",),
            )
        return []
    if b == ALEF:
        return []
    if b == YEH:
        if last.has(SHADDA):
            return one(FinalClass.SOUND, 0.95)
        if prev is not None and prev.has(KASRA):
            return one(FinalClass.MANQUS, 0.9)
        if prev is not None and prev.has(SUKUN):
            return one(FinalClass.SOUND, 0.9)
        return [
            Interpretation(
                stem=stem, final_class=FinalClass.MANQUS, source=Source.HEURISTIC, confidence=0.5,
                condition="If the yeh is preceded by kasra (manqus, like قاضي).",
            ),
            Interpretation(
                stem=stem, final_class=FinalClass.SOUND, source=Source.HEURISTIC, confidence=0.5,
                condition="If the yeh is doubled or follows sukun (like كرسيّ or ظبْي).",
            ),
        ]
    if b == HAMZA and prev is not None and prev.base == ALEF and n >= 3:
        return one(FinalClass.MAMDUD, 0.9)
    return one(FinalClass.SOUND, 0.95)
