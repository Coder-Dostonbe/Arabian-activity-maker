"""Generate dual (المثنى) forms of a singular noun.

Pipeline: parse the input → classify the final letter (lexicon first, then
spelling) → apply the matching rule → attach the case/state suffix.
"""

from __future__ import annotations

from .chars import (
    ALEF,
    ALEF_HAMZA_ABOVE,
    ALEF_MADDA,
    CASE_MARKS,
    FATHA,
    HAMZA,
    KASRA,
    NOON,
    SHADDA,
    SUKUN,
    TEH,
    TEH_MARBUTA,
    WAW,
    WAW_HAMZA,
    YEH,
    YEH_HAMZA,
)
from .classify import Interpretation
from .clusters import Cluster, join_clusters
from .lexicon import Lexicon
from .normalize import strip_diacritics
from .orthography import add_article
from .pipeline import Prepared, finish, prepare
from .rules import get_rule
from .types import (
    AlifOrigin,
    Case,
    FinalClass,
    GeneratedForm,
    GenerationResult,
    HamzaType,
    Number,
)


def generate_dual(
    word: str,
    case: Case = Case.NOMINATIVE,
    *,
    definite: bool | None = None,
    construct: bool = False,
    lexicon: Lexicon | None = None,
) -> GenerationResult:
    """Dual of `word` in `case`. `definite=None` keeps the input's definiteness."""
    prep = prepare(word, definite=definite, construct=construct, lexicon=lexicon)
    if not isinstance(prep, Prepared):
        return prep

    forms: list[GeneratedForm] = []
    ambiguous = len(prep.interpretations) > 1
    for interp in prep.interpretations:
        variants, uncertain = stem_variants(interp, alif_suffix=case is Case.NOMINATIVE)
        ambiguous = ambiguous or uncertain
        for stem, rule_id, merge_madda, condition, factor in variants:
            forms.append(_build(interp, stem, rule_id, merge_madda, condition, factor, case, prep.definite, construct))
    return finish(word, forms, prep.warnings, ambiguous,
                  "No dual rule applies to this word with the available information.")


def dual_paradigm(word: str, *, lexicon: Lexicon | None = None) -> dict[str, dict[str, GenerationResult]]:
    """All three cases for the indefinite, definite and construct states."""
    states = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}
    return {
        state: {c.value: generate_dual(word, c, definite=d, construct=k, lexicon=lexicon) for c in Case}
        for state, (d, k) in states.items()
    }


def stem_variants(interp: Interpretation, *, alif_suffix: bool):
    """Final-letter changes before the dual suffix.

    `alif_suffix` is True when the suffix starts with alif (ـان, and ـات in the
    sound feminine plural, which treats these endings the same way).
    Returns ([(stem, rule_id, merge_madda, condition, confidence_factor)], uncertain).
    """
    stem = list(interp.stem)
    last = stem[-1]
    b = last.base
    nominative = alif_suffix

    def swap(base: str) -> list[Cluster]:
        return stem[:-1] + [Cluster(base, "".join(m for m in last.marks if m == SHADDA))]

    cls = interp.final_class
    if cls is FinalClass.SOUND:
        if b == TEH_MARBUTA:
            return [(swap(TEH), "dual.teh_marbuta", False, None, 1.0)], False
        if b == ALEF_HAMZA_ABOVE:
            return [(stem, "dual.hamza.alif_seat", nominative, None, 1.0)], False
        if b == HAMZA and len(stem) >= 2:
            prev = stem[-2].base
            if prev == YEH:
                return [(swap(YEH_HAMZA), "dual.hamza.after_yeh", False, None, 1.0)], False
            if prev == WAW:
                return [(stem, "dual.hamza.after_waw", False, None, 1.0)], False
            new = stem if nominative else swap(ALEF_HAMZA_ABOVE)
            return [(new, "dual.hamza.after_sakin_consonant", False, None, 1.0)], False
        if b in (YEH_HAMZA, WAW_HAMZA):
            return [(stem, "dual.hamza.seat_kept", False, None, 1.0)], False
        return [(stem, "dual.sound", False, None, 1.0)], False

    if cls is FinalClass.MAQSUR:
        if len(stem) >= 4:
            return [(swap(YEH), "dual.maqsur.over_three", False, None, 1.0)], False
        if interp.alif_origin is AlifOrigin.WAW:
            return [(swap(WAW), "dual.maqsur.trilateral_waw", False, None, 1.0)], False
        if interp.alif_origin is AlifOrigin.YEH:
            return [(swap(YEH), "dual.maqsur.trilateral_yeh", False, None, 1.0)], False
        return [], False

    if cls is FinalClass.MANQUS:
        return [(stem, "dual.manqus", False, None, 1.0)], False

    # MAMDUD
    ht = interp.hamza_type
    if ht is HamzaType.ORIGINAL:
        return [(stem, "dual.mamdud.original", False, None, 1.0)], False
    if ht is HamzaType.FEMININE:
        return [(swap(WAW), "dual.mamdud.feminine", False, None, 1.0)], False
    if ht in (HamzaType.SUBSTITUTED, HamzaType.ILHAQ):
        rule = "dual.mamdud.substituted" if ht is HamzaType.SUBSTITUTED else "dual.mamdud.ilhaq"
        return [
            (stem, rule, False, "Both forms are valid.", 1.0),
            (swap(WAW), rule, False, "Both forms are valid.", 1.0),
        ], False
    return [
        (stem, "dual.mamdud.original", False,
         "Valid if the hamza is original, substituted for waw/yeh, or for ilḥāq.", 0.55),
        (swap(WAW), "dual.mamdud.feminine", False,
         "Valid if the hamza marks the feminine (like صحراء), or is substituted/for ilḥāq.", 0.55),
    ], True


def _build(interp, stem, rule_id, merge_madda, condition, factor, case, definite, construct) -> GeneratedForm:
    nominative = case is Case.NOMINATIVE
    stem = list(stem)
    if merge_madda:
        stem[-1] = Cluster(ALEF_MADDA)
        tail = []
    else:
        last = stem[-1].without(CASE_MARKS)
        stem[-1] = last.with_marks(last.marks + FATHA)
        tail = [Cluster(ALEF)] if nominative else [Cluster(YEH, SUKUN)]
    if not construct:
        tail.append(Cluster(NOON, KASRA))
    body = stem + tail

    if definite:
        body = add_article(body)

    vocalized = join_clusters(body)
    rule_ids = (rule_id, "dual.construct_nun_drop") if construct else (rule_id,)
    confidence = round(min(interp.confidence, get_rule(rule_id).confidence) * factor, 2)
    conditions = [c for c in (interp.condition, condition) if c]
    warnings = list(interp.warnings)
    if construct and not nominative:
        warnings.append("Before a word starting with hamzat al-waṣl the yeh takes kasra (كتابَيِ الطالبِ).")
    return GeneratedForm(
        text=strip_diacritics(vocalized),
        vocalized=vocalized,
        number=Number.DUAL,
        case=case,
        definite=definite,
        construct=construct,
        rule_ids=rule_ids,
        source=interp.source,
        confidence=confidence,
        condition=" ".join(conditions) or None,
        warnings=tuple(warnings),
    )
