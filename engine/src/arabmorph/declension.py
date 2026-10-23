"""Case endings for nouns declined with short vowels (الإعراب بالحركات).

Used for singulars, broken plurals and (for the final ta) the sound feminine
plural. The dual and sound masculine plural decline with letters and build
their own suffixes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chars import (
    ALEF,
    ALEF_HAMZA_ABOVE,
    ALEF_MAQSURA,
    DAMMA,
    DAMMATAN,
    FATHA,
    FATHATAN,
    HAMZA,
    KASRA,
    KASRATAN,
    SHADDA,
    TEH_MARBUTA,
    YEH,
)
from .clusters import Cluster
from .orthography import add_mark
from .types import Case, FinalClass


@dataclass(frozen=True)
class Declined:
    clusters: list[Cluster]
    rule_ids: tuple[str, ...]


def final_class_by_spelling(stem) -> FinalClass:
    """Final class of an already-known (e.g. lexicon) vocalised form."""
    last = stem[-1]
    if last.base in (ALEF, ALEF_MAQSURA):
        return FinalClass.MAQSUR
    if last.base == YEH and not last.has(SHADDA) and len(stem) >= 2 and stem[-2].has(KASRA):
        return FinalClass.MANQUS
    return FinalClass.SOUND


def takes_tanween_alif(stem) -> bool:
    """Accusative tanween is written with an extra alif, except after ة, ى, أ and ـاء."""
    last = stem[-1].base
    if last in (TEH_MARBUTA, ALEF_MAQSURA, ALEF_HAMZA_ABOVE):
        return False
    if last == HAMZA and len(stem) >= 2 and stem[-2].base == ALEF:
        return False
    return True


def decline(stem, case: Case, *, definite: bool, construct: bool, diptote: bool,
            final_class: FinalClass) -> Declined:
    stem = list(stem)
    indefinite = not (definite or construct)

    if final_class is FinalClass.MAQSUR:
        # Case is implicit (مقدّرة) on the alif; only the tanween is visible.
        if indefinite and not diptote:
            stem[-2] = add_mark(stem[-2], FATHATAN)
        return Declined(stem, ("decl.maqsur",))

    if final_class is FinalClass.MANQUS:
        rule = "decl.manqus_diptote" if diptote else "decl.manqus"
        if case is Case.ACCUSATIVE:
            if indefinite and not diptote:
                stem[-1] = add_mark(stem[-1], FATHATAN)
                return Declined(stem + [Cluster(ALEF)], (rule,))
            stem[-1] = add_mark(stem[-1], FATHA)
            return Declined(stem, (rule,))
        if indefinite:
            # The yeh drops and tanween falls on the preceding letter (قاضٍ، ليالٍ).
            body = stem[:-1]
            body[-1] = add_mark(body[-1], KASRATAN)
            return Declined(body, (rule,))
        stem[-1] = stem[-1].without_case_marks()
        return Declined(stem, (rule,))

    # Sound ending (including ta marbuta and final hamza).
    if diptote:
        if indefinite:
            vowel = {Case.NOMINATIVE: DAMMA, Case.ACCUSATIVE: FATHA, Case.GENITIVE: FATHA}[case]
            rules = ("decl.diptote",)
        else:
            vowel = {Case.NOMINATIVE: DAMMA, Case.ACCUSATIVE: FATHA, Case.GENITIVE: KASRA}[case]
            rules = ("decl.diptote", "decl.diptote_kasra_when_definite") if case is Case.GENITIVE else ("decl.diptote",)
        stem[-1] = add_mark(stem[-1], vowel)
        return Declined(stem, rules)

    if indefinite:
        mark = {Case.NOMINATIVE: DAMMATAN, Case.ACCUSATIVE: FATHATAN, Case.GENITIVE: KASRATAN}[case]
        stem[-1] = add_mark(stem[-1], mark)
        if case is Case.ACCUSATIVE:
            if takes_tanween_alif(stem):
                return Declined(stem + [Cluster(ALEF)], ("decl.triptote", "decl.tanween_alif"))
            return Declined(stem, ("decl.triptote", "decl.tanween_alif_omitted"))
        return Declined(stem, ("decl.triptote",))

    vowel = {Case.NOMINATIVE: DAMMA, Case.ACCUSATIVE: FATHA, Case.GENITIVE: KASRA}[case]
    stem[-1] = add_mark(stem[-1], vowel)
    return Declined(stem, ("decl.triptote",))
