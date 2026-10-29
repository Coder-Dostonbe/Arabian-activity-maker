"""Parse a single Arabic noun as typed by a user.

Separates what the user typed (kept verbatim) from the stem the rules work
on: the definite article and the case ending on the final letter are removed
and recorded, everything else - including partial diacritics - is preserved.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .chars import (
    ALEF,
    ALEF_WASLA,
    FATHA,
    FATHATAN,
    KASRATAN,
    LAM,
    SHADDA,
    SUN_LETTERS,
    is_arabic_letter,
)
from .clusters import Cluster, bare, has_any_marks, split_clusters
from .normalize import fold_input


class InputError(ValueError):
    """The input cannot be processed as a single Arabic word."""


@dataclass(frozen=True)
class ParsedNoun:
    original: str
    stem: tuple[Cluster, ...]   # no article; case marks removed from the final letter
    definite: bool              # input carried the definite article
    tanween_alif: bool          # final ا written with fathatan (accusative spelling, or maqsur عصًا)
    final_kasratan: bool        # final letter carried kasratan (may hide a dropped manqus yeh)
    vocalized: bool
    warnings: tuple[str, ...] = ()
    final_persian_yeh: bool = False   # the final ي was typed as Persian ی (may stand for ى)


_DUAL_PLURAL_ENDINGS = ("ان", "ين", "ون", "ات")


def parse_noun(word: str) -> ParsedNoun:
    folded = fold_input(unicodedata.normalize("NFC", word).strip())
    text = folded.text.strip()
    if not text:
        raise InputError("Input is empty.")
    if any(ch.isspace() for ch in text):
        raise InputError("Expected a single word; the input contains whitespace.")
    try:
        clusters = split_clusters(text)
    except ValueError as exc:
        raise InputError(f"Malformed input: {exc}.") from exc
    foreign = sorted({c.base for c in clusters if not is_arabic_letter(c.base)})
    if foreign:
        raise InputError(f"Input contains non-Arabic characters: {' '.join(foreign)}")

    warnings: list[str] = list(folded.warnings)
    definite = False
    if len(clusters) >= 4 and clusters[0].base in (ALEF, ALEF_WASLA) and clusters[1].base == LAM:
        definite = True
        clusters = clusters[2:]
        first = clusters[0]
        # The shadda on a sun letter after ال is assimilation, not part of the stem.
        if first.base in SUN_LETTERS and first.has(SHADDA):
            clusters[0] = first.without({SHADDA})
        warnings.append("Leading ال was treated as the definite article.")

    if len(clusters) < 2:
        raise InputError("Word is too short to be analysed as a noun.")

    last = clusters[-1]
    final_kasratan = last.has(KASRATAN)
    tanween_alif = last.base == ALEF and (
        last.has(FATHATAN) or clusters[-2].has(FATHATAN)
    )
    clusters[-1] = last.without_case_marks()
    if tanween_alif and clusters[-2].has(FATHATAN):
        # Keep the fatha so a maqsur reading (عَصًا → عَصَا) stays vocalised.
        prev = clusters[-2].without({FATHATAN})
        clusters[-2] = prev.with_marks(prev.marks + FATHA)

    if bare(clusters).endswith(_DUAL_PLURAL_ENDINGS) and len(clusters) >= 4:
        warnings.append("The word ends like a dual or plural; it is assumed to be singular.")

    return ParsedNoun(
        original=word,
        stem=tuple(clusters),
        definite=definite,
        tanween_alif=tanween_alif,
        final_kasratan=final_kasratan,
        vocalized=has_any_marks(split_clusters(text)),
        warnings=tuple(warnings),
        final_persian_yeh=folded.final_persian_yeh,
    )
