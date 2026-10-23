"""Case assignment from the immediately preceding governing word (العامل).

Deliberately narrow: only governors whose effect on the *next* noun is
reliable are recognised. Anything else returns no case and says why, rather
than guessing — full syntactic analysis is out of scope here.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace

from .chars import SHADDA
from .lexicon import Lexicon
from .normalize import strip_diacritics
from .pipeline import ASSUMPTIONS, error
from .types import Case, GenerationResult, Number, PluralKind

PREPOSITIONS = {"في", "من", "إلى", "الى", "عن", "على"}
INNA_SISTERS = {"إن", "أن", "كأن", "لكن", "ليت", "لعل"}
SHADDA_REQUIRED = {"إن", "أن", "كأن", "لكن"}   # without shadda they are different particles
KANA_SISTERS = {
    "كان", "كانت", "أصبح", "أصبحت", "أمسى", "أمست", "أضحى", "أضحت",
    "ظل", "ظلت", "بات", "باتت", "صار", "صارت", "ليس", "ليست",
}


@dataclass(frozen=True)
class ContextCase:
    case: Case | None
    rule_id: str | None
    confidence: float
    warnings: tuple[str, ...] = ()


def case_from_context(preceding: str) -> ContextCase:
    word = unicodedata.normalize("NFC", preceding).strip()
    bare = strip_diacritics(word)

    if bare in PREPOSITIONS:
        warns = ()
        conf = 0.95
        if bare == "من" and SHADDA not in word and "ِ" not in word:
            conf = 0.8
            warns = ("Undiacritized من could be the pronoun مَن (who), which does not govern the genitive.",)
        return ContextCase(Case.GENITIVE, "context.preposition_genitive", conf, warns)

    if bare in INNA_SISTERS:
        if bare in SHADDA_REQUIRED and SHADDA not in word:
            return ContextCase(None, None, 0.0, (
                f"{bare} without shadda may be a different particle (e.g. إنْ، أنْ، لكنْ) that does not "
                f"make the next noun accusative; write the shadda ({bare}ّ) to disambiguate.",
            ))
        return ContextCase(Case.ACCUSATIVE, "context.inna_accusative", 0.9, (
            "Assumes the noun directly follows the particle as its subject (اسم إنّ).",
        ))

    if bare in KANA_SISTERS:
        return ContextCase(Case.NOMINATIVE, "context.kana_nominative", 0.7, (
            "Assumes the noun is the subject of the verb (اسم كان); a fronted predicate or another "
            "construction would change the case.",
        ))

    return ContextCase(None, None, 0.0, (
        f"No governing word recognised in «{preceding}»; the case requires syntactic analysis, "
        "which is not supported yet.",
    ))


def generate_in_context(
    word: str,
    number: Number,
    preceding: str,
    *,
    definite: bool | None = None,
    construct: bool = False,
    kind: PluralKind | None = None,
    lexicon: Lexicon | None = None,
) -> GenerationResult:
    """Generate `word` in the case required by the word before it."""
    from .generate import generate  # local import: generate.py is the higher-level module

    ctx = case_from_context(preceding)
    if ctx.case is None:
        return error(word, "The case could not be determined from the context.", ctx.warnings)

    result = generate(word, number, ctx.case, definite=definite, construct=construct, kind=kind, lexicon=lexicon)
    forms = tuple(
        replace(f, rule_ids=(ctx.rule_id, *f.rule_ids),
                confidence=round(min(f.confidence, ctx.confidence), 2),
                warnings=tuple(dict.fromkeys((*f.warnings, *ctx.warnings))))
        for f in result.forms
    )
    return replace(result, forms=forms, assumptions=tuple(a for a in ASSUMPTIONS if "sentence context" not in a
                                                          and "case comes from" not in a)
                   + (f"The case was taken from the preceding word «{preceding}».",))
