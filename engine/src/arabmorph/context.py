"""Case assignment from the immediately preceding governing word (العامل).

Deliberately narrow: only governors whose effect on the *next* noun is
reliable are recognised. Anything else returns no case and says why, rather
than guessing — full syntactic analysis is out of scope here.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field, replace

from .chars import ALEF, ALEF_MAQSURA, DAMMA, FATHA, KASRA, SHADDA, TANWEEN
from .clusters import Cluster, join_clusters, split_clusters
from .function_words import (
    ADVERBS_MUDAF,
    HAMZALESS_INNA,
    INNA_SISTERS,
    KANA_CONJUGATED,
    KANA_SISTERS,
    KANA_WITH_PRONOUN,
    LA_NAFIYA,
    PREPOSITIONS,
    QUALIFIED_PREPOSITIONS,
    SHADDA_REQUIRED,
)
from .lexicon import Lexicon
from .normalize import fold_input, strip_diacritics
from .pipeline import ASSUMPTIONS, error
from .types import Case, GeneratedForm, GenerationResult, Number, PluralKind, Status

_KNOWN = (PREPOSITIONS | set(QUALIFIED_PREPOSITIONS) | ADVERBS_MUDAF | INNA_SISTERS | KANA_SISTERS
          | KANA_CONJUGATED | KANA_WITH_PRONOUN | LA_NAFIYA)


@dataclass(frozen=True)
class ContextCase:
    case: Case | None
    rule_id: str | None
    confidence: float
    warnings: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = field(default=())
    la_nafiya: bool = False      # the noun is the subject of لا النافية للجنس (built without tanween)


def _fold(preceding: str) -> tuple[str, str, list[str]]:
    """(vocalised, bare) spelling of the governor; a final Persian ی becomes ى when that names a governor."""
    folded = fold_input(" ".join(unicodedata.normalize("NFC", preceding).split()))
    word, warnings = folded.text, list(folded.warnings)
    bare = strip_diacritics(word)
    if folded.final_persian_yeh and bare not in _KNOWN and bare[:-1] + ALEF_MAQSURA in _KNOWN:
        bare = bare[:-1] + ALEF_MAQSURA
        clusters = split_clusters(word)
        clusters[-1] = Cluster(ALEF_MAQSURA, clusters[-1].marks)
        word = join_clusters(clusters)
        warnings.append(f"The final ی was read as ى («{bare}»).")
    return word, bare, warnings


def case_from_context(preceding: str) -> ContextCase:
    word, bare, notes = _fold(preceding)

    def found(case, rule_id, conf, *warns, **kw) -> ContextCase:
        return ContextCase(case, rule_id, conf, tuple(notes) + warns, **kw)

    if bare in PREPOSITIONS:
        warns = ()
        conf = 0.95
        if bare == "من" and SHADDA not in word and KASRA not in word:
            conf = 0.8
            warns = ("Undiacritized من could be the pronoun مَن (who), which does not govern the genitive.",)
        if bare == "الى":
            warns = ("The standard spelling is إلى (with hamza).",)
        return found(Case.GENITIVE, "context.preposition_genitive", conf, *warns,
                     suggestions=("إلى",) if bare == "الى" else ())

    if bare in QUALIFIED_PREPOSITIONS:
        return found(Case.GENITIVE, "context.preposition_genitive_qualified", 0.7, QUALIFIED_PREPOSITIONS[bare])

    if bare in ADVERBS_MUDAF:
        return found(Case.GENITIVE, "context.adverb_mudaf_genitive", 0.85,
                     f"Assumes the noun is the muḍāf ilayh of the adverb {bare} (e.g. {bare} الدرسِ), "
                     "directly after it.")

    if bare in INNA_SISTERS:
        if bare in SHADDA_REQUIRED and SHADDA not in word:
            return found(None, None, 0.0,
                         f"{bare} without shadda may be a different particle (e.g. إنْ، أنْ، لكنْ) that does not "
                         f"make the next noun accusative; write the shadda ({bare}ّ) to disambiguate.")
        return found(Case.ACCUSATIVE, "context.inna_accusative", 0.9,
                     "Assumes the noun directly follows the particle as its subject (اسم إنّ).")

    if bare in HAMZALESS_INNA:
        options = HAMZALESS_INNA[bare]
        return found(None, None, 0.0,
                     f"«{bare}» is written without hamza; did you mean {' or '.join(options)}? "
                     "Both make the next noun accusative once the hamza and shadda are written.",
                     suggestions=options)

    if bare in KANA_SISTERS:
        return found(Case.NOMINATIVE, "context.kana_nominative", 0.7,
                     "Assumes the noun is the subject of the verb (اسم كان); a fronted predicate or another "
                     "construction would change the case.")

    if bare in KANA_CONJUGATED:
        warns = ["Assumes the noun is the subject of the verb (اسم كان), directly after it."]
        if bare.startswith("ت") or " ت" in bare:
            warns.append(f"{bare} can also be second person (you are …); then the noun is the predicate "
                         "and accusative.")
        if bare.startswith("ما دام"):
            warns.append("ما دام needs a preceding clause (سأبقى ما دام المطرُ نازلًا).")
        return found(Case.NOMINATIVE, "context.kana_conjugated_nominative", 0.65, *warns)

    if bare in KANA_WITH_PRONOUN:
        return found(Case.ACCUSATIVE, "context.kana_pronoun_predicate_accusative", 0.65,
                     f"The pronoun attached to {bare} is its subject; assumes the noun is the predicate "
                     "(خبر كان), directly after it.")

    if bare in LA_NAFIYA:
        return found(Case.ACCUSATIVE, "context.la_nafiya_lil_jins", 0.6,
                     "Assumes لا negates the whole class (لا النافية للجنس) and is directly followed by its noun; "
                     "a simple لا (لا أعرف) or لا acting like ليس would change the case.",
                     la_nafiya=True)

    return found(None, None, 0.0,
                 f"No governing word recognised in «{preceding}»; the case requires syntactic analysis, "
                 "which is not supported yet.")


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
        return error(word, "The case could not be determined from the context.", ctx.warnings, ctx.suggestions)

    result = generate(word, number, ctx.case, definite=definite, construct=construct, kind=kind, lexicon=lexicon)
    forms = result.forms
    if ctx.la_nafiya and result.status is not Status.ERROR:
        if any(f.definite for f in forms):
            return error(word, "لا النافية للجنس governs only an indefinite noun; with ال the لا is a "
                               "different particle.", ctx.warnings)
        forms = tuple(f if f.construct else _without_tanween(f) for f in forms)
    forms = tuple(
        replace(f, rule_ids=(ctx.rule_id, *f.rule_ids),
                confidence=round(min(f.confidence, ctx.confidence), 2),
                warnings=tuple(dict.fromkeys((*f.warnings, *ctx.warnings))))
        for f in forms
    )
    return replace(result, forms=forms,
                   suggestions=tuple(dict.fromkeys((*result.suggestions, *ctx.suggestions))),
                   assumptions=tuple(a for a in ASSUMPTIONS if "sentence context" not in a
                                     and "case comes from" not in a)
                   + (f"The case was taken from the preceding word «{preceding}».",))


_SHORT = {"ً": FATHA, "ٌ": DAMMA, "ٍ": KASRA}


def _without_tanween(form: GeneratedForm) -> GeneratedForm:
    """لا رجلَ / لا طالباتِ / لا فتى: the noun of لا is built on its accusative ending without tanween."""
    clusters = split_clusters(form.vocalized)
    warnings = list(form.warnings)
    for i in range(len(clusters) - 1, max(len(clusters) - 3, -1), -1):
        c = clusters[i]
        mark = next((m for m in c.marks if m in TANWEEN), None)
        if mark is None:
            continue
        clusters[i] = c.without(TANWEEN).with_marks(c.without(TANWEEN).marks + _SHORT[mark])
        if i == len(clusters) - 2 and clusters[-1].base == ALEF and not clusters[-1].marks:
            clusters.pop()   # the tanween alif goes with the tanween (رجلًا ← رجلَ)
        if mark == "ٍ":
            warnings.append("A sound feminine plural after لا may also take fatha (لا طالباتَ).")
        break
    vocalized = join_clusters(clusters)
    return replace(form, vocalized=vocalized, text=strip_diacritics(vocalized), warnings=tuple(warnings))
