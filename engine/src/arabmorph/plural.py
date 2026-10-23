"""Plural forms: sound masculine (ـون/ـين), sound feminine (ـات), broken.

Which plural a noun takes is a lexical fact, not something spelling reveals
(كتاب → كُتُب, never كتابون). Plurals therefore come from lexicon entries; the
caller may also assert a sound-plural kind explicitly, which is recorded as
the form's source.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chars import (
    ALEF,
    ALEF_HAMZA_ABOVE,
    ALEF_MADDA,
    DAMMA,
    DAMMATAN,
    FATHA,
    HAMZA,
    KASRA,
    KASRATAN,
    NOON,
    SUKUN,
    TEH,
    TEH_MARBUTA,
    WAW,
    WAW_HAMZA,
    YEH,
    YEH_HAMZA,
)
from .classify import Interpretation
from .clusters import Cluster, join_clusters, split_clusters
from .declension import decline, final_class_by_spelling
from .dual import stem_variants
from .lexicon import Lexicon, LexiconEntry, PluralSpec
from .normalize import strip_diacritics
from .orthography import add_article, add_mark
from .pipeline import Prepared, finish, prepare
from .rules import get_rule
from .types import (
    AlifOrigin,
    Case,
    FinalClass,
    Gender,
    GeneratedForm,
    GenerationResult,
    HamzaType,
    Number,
    PluralKind,
    Source,
)

ASSERTED_CONFIDENCE = 0.6
CANDIDATE_CONFIDENCE = 0.4


@dataclass(frozen=True)
class Variant:
    stem: list[Cluster]
    rule_ids: tuple[str, ...]
    merge_madda: bool = False
    condition: str | None = None
    factor: float = 1.0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Request:
    case: Case
    definite: bool
    construct: bool

    @property
    def indefinite(self) -> bool:
        return not (self.definite or self.construct)


def generate_plural(
    word: str,
    case: Case = Case.NOMINATIVE,
    *,
    definite: bool | None = None,
    construct: bool = False,
    kind: PluralKind | None = None,
    lexicon: Lexicon | None = None,
) -> GenerationResult:
    """Plural(s) of `word`. With `kind`, only that plural type is produced."""
    prep = prepare(word, definite=definite, construct=construct, lexicon=lexicon)
    if not isinstance(prep, Prepared):
        return prep
    req = _Request(case, prep.definite, construct)
    warnings = prep.warnings
    forms: list[GeneratedForm] = []
    reasons: list[str] = []
    ambiguous = len(prep.interpretations) > 1

    for interp in prep.interpretations:
        entry = prep.lexicon.get(interp.entry_id) if interp.entry_id else None
        if entry is not None:
            specs = [s for s in entry.plurals if kind is None or s.kind is kind]
            if specs:
                for spec in specs:
                    new, uncertain = _forms(interp, entry, spec, req, Source.LEXICON, None, 1.0, reasons)
                    forms += new
                    ambiguous = ambiguous or uncertain
                continue
            if kind is None:
                warnings.append(f"No plural is recorded for lexicon entry {entry.lemma} ({entry.id}).")
                continue

        if kind is PluralKind.BROKEN:
            warnings.append("Broken plurals are produced only from lexicon entries; none is recorded for this reading.")
        elif kind is not None:
            cond = f"The caller asserted that this word takes the {kind.value.replace('_', ' ')} plural; not verified."
            new, uncertain = _forms(interp, entry, PluralSpec(kind), req, Source.ASSERTED, cond, ASSERTED_CONFIDENCE, reasons)
            forms += new
            ambiguous = ambiguous or uncertain
        elif interp.stem[-1].base == TEH_MARBUTA:
            cond = ("Only if this noun takes the sound feminine plural; many nouns in ة take a broken "
                    "plural instead (مدرسة ← مدارس).")
            new, _ = _forms(interp, entry, PluralSpec(PluralKind.SOUND_FEMININE), req,
                            Source.HEURISTIC, cond, CANDIDATE_CONFIDENCE, reasons)
            forms += new
            ambiguous = True

    if reasons and not forms:
        return finish(word, forms, warnings, ambiguous, " ".join(dict.fromkeys(reasons)))
    warnings.extend(reasons)
    return finish(
        word, forms, warnings, ambiguous,
        "No plural can be determined: the word has no lexicon entry with a recorded plural, and the "
        "plural type cannot be inferred from spelling. Pass a plural kind to apply a sound-plural rule.",
    )


def _forms(interp: Interpretation, entry: LexiconEntry | None, spec: PluralSpec, req: _Request,
           source: Source, condition: str | None, cap: float,
           reasons: list[str]) -> tuple[list[GeneratedForm], bool]:
    """Forms for one plural spec; reasons for producing none are appended to `reasons`."""
    if spec.kind is PluralKind.BROKEN:
        return [_broken(interp, spec, req, source, condition, cap)], False

    extra: list[str] = []
    if spec.kind is PluralKind.SOUND_FEMININE:
        variants, uncertain = _feminine_variants(interp, entry)
    else:
        if entry is not None and entry.gender is Gender.FEMININE:
            extra.append("The lexicon marks this word as feminine; the sound masculine plural is unexpected.")
        variants, uncertain, reason = _masculine_variants(interp, req.case)
        if reason:
            reasons.append(reason)
            return [], False

    forms = []
    for v in variants:
        if spec.kind is PluralKind.SOUND_FEMININE:
            body, rules = _attach_feminine(v, req)
        else:
            body, rules = _attach_masculine(v, req)
        forms.append(_form(interp, body, rules, req, source, spec, cap * v.factor,
                           [c for c in (interp.condition, condition, v.condition) if c],
                           [*interp.warnings, *v.warnings, *extra]))
    return forms, uncertain


def _broken(interp, spec: PluralSpec, req: _Request, source, condition, cap) -> GeneratedForm:
    stem = split_clusters(spec.form)
    declined = decline(stem, req.case, definite=req.definite, construct=req.construct,
                       diptote=spec.diptote, final_class=final_class_by_spelling(stem))
    rules = ("plural.broken.lexicon", *declined.rule_ids)
    conds = [c for c in (interp.condition, condition, spec.note or None) if c]
    return _form(interp, declined.clusters, rules, req, source, spec, cap, conds, list(interp.warnings))


def _feminine_variants(interp: Interpretation, entry: LexiconEntry | None) -> tuple[list[Variant], bool]:
    stem = list(interp.stem)
    base_rules = ("plural.fem.sound",)
    if interp.final_class is FinalClass.SOUND and stem[-1].base == TEH_MARBUTA:
        s = stem[:-1]
        rules = (*base_rules, "plural.fem.teh_marbuta_dropped")
        prev = s[-1]
        if prev.base == ALEF:
            rules = (*rules, "plural.fem.alif_before_teh")
            if len(s) >= 4:
                return [Variant(s[:-1] + [Cluster(YEH)], rules)], False
            origin = entry.alif_origin if entry else None
            if origin is not None:
                return [Variant(s[:-1] + [Cluster(WAW if origin is AlifOrigin.WAW else YEH)], rules)], False
            return [
                Variant(s[:-1] + [Cluster(WAW)], rules, condition="If the alif derives from waw (صلاة ← صلوات).", factor=0.5),
                Variant(s[:-1] + [Cluster(YEH)], rules, condition="If the alif derives from yeh (فتاة ← فتيات).", factor=0.5),
            ], True
        if prev.base == ALEF_HAMZA_ABOVE:
            return [Variant(s, (*rules, "plural.fem.hamza_madda"), merge_madda=True)], False
        s, itbaa_rules, warns = _itbaa(s, entry)
        return [Variant(s, (*rules, *itbaa_rules), warnings=warns)], False

    variants, uncertain = stem_variants(interp, alif_suffix=True)
    out = []
    for v_stem, rule_id, merge, cond, factor in variants:
        rules = base_rules if rule_id == "dual.sound" else (*base_rules, rule_id)
        out.append(Variant(v_stem, rules, merge, cond, factor))
    return out, uncertain


def _itbaa(s: list[Cluster], entry: LexiconEntry | None) -> tuple[list[Cluster], tuple[str, ...], tuple[str, ...]]:
    """فَعْلة nouns move the middle letter to fatha before ـات (سَجْدة ← سَجَدات)."""
    if len(s) != 3 or not s[1].has(SUKUN) or s[1].base in (WAW, YEH) or s[1].base == s[2].base:
        return s, (), ()
    if s[0].has(FATHA):
        pos = entry.pos if entry else None
        if pos not in (None, "noun"):
            return s, (), ()
        warns = () if pos else ("Assumed to be a noun; adjectives keep the sukun (ضَخْمة ← ضَخْمات).",)
        return [s[0], add_mark(s[1], FATHA), s[2]], ("plural.fem.itbaa",), warns
    if s[0].has(DAMMA) or s[0].has(KASRA):
        return s, (), ("The middle letter may also follow the first vowel or take fatha "
                       "(غُرْفة ← غُرُفات / غُرَفات / غُرْفات); only the form with sukun is given.",)
    return s, (), ()


def _attach_feminine(v: Variant, req: _Request) -> tuple[list[Cluster], tuple[str, ...]]:
    stem = list(v.stem)
    nominative = req.case is Case.NOMINATIVE
    if req.indefinite:
        mark = DAMMATAN if nominative else KASRATAN
    else:
        mark = DAMMA if nominative else KASRA
    if v.merge_madda:
        stem[-1] = Cluster(ALEF_MADDA)
        body = stem + [Cluster(TEH, mark)]
    else:
        stem[-1] = add_mark(stem[-1], FATHA)
        body = stem + [Cluster(ALEF), Cluster(TEH, mark)]
    rules = v.rule_ids + (("plural.fem.accusative_kasra",) if req.case is Case.ACCUSATIVE else ())
    return body, rules


def _masculine_variants(interp: Interpretation, case: Case) -> tuple[list[Variant], bool, str | None]:
    stem = list(interp.stem)
    last = stem[-1]
    nominative = case is Case.NOMINATIVE
    cls = interp.final_class
    if cls is FinalClass.MAMDUD and interp.hamza_type is not HamzaType.ORIGINAL:
        return [], False, "The sound masculine plural of this mamdud noun is not supported yet."
    if cls in (FinalClass.SOUND, FinalClass.MAMDUD):
        if last.base == TEH_MARBUTA:
            return [], False, "Nouns ending in ta marbuta do not take the sound masculine plural."
        rules = ("plural.masc.sound",)
        if last.base == HAMZA and len(stem) >= 2 and stem[-2].base == YEH:
            stem[-1] = Cluster(YEH_HAMZA)
            rules = (*rules, "plural.masc.hamza_seat")
        elif last.base in (ALEF_HAMZA_ABOVE, WAW_HAMZA) or (last.base == HAMZA and cls is FinalClass.SOUND):
            return [], False, "Hamza spelling before ـون/ـين is not supported yet for this ending."
        stem[-1] = add_mark(stem[-1], DAMMA if nominative else KASRA)
        return [Variant(stem + [Cluster(WAW if nominative else YEH)], rules)], False, None
    if cls is FinalClass.MAQSUR:
        body = stem[:-1]
        body[-1] = add_mark(body[-1], FATHA)
        return [Variant(body + [Cluster(WAW if nominative else YEH, SUKUN)], ("plural.masc.maqsur",))], False, None
    # MANQUS: the yeh drops; the preceding letter takes the vowel of the ending.
    body = stem[:-1]
    body[-1] = add_mark(body[-1], DAMMA if nominative else KASRA)
    return [Variant(body + [Cluster(WAW if nominative else YEH)], ("plural.masc.manqus",))], False, None


def _attach_masculine(v: Variant, req: _Request) -> tuple[list[Cluster], tuple[str, ...]]:
    if req.construct:
        return list(v.stem), v.rule_ids + ("plural.masc.construct_nun_drop",)
    return list(v.stem) + [Cluster(NOON, FATHA)], v.rule_ids


def _form(interp, body, rules, req: _Request, source, spec: PluralSpec, cap, conditions, warnings) -> GeneratedForm:
    if req.definite:
        body = add_article(list(body))
    vocalized = join_clusters(body)
    confidence = round(min(interp.confidence, get_rule(rules[0]).confidence, cap), 2)
    return GeneratedForm(
        text=strip_diacritics(vocalized),
        vocalized=vocalized,
        number=Number.PLURAL,
        case=req.case,
        definite=req.definite,
        construct=req.construct,
        rule_ids=tuple(rules),
        source=source,
        confidence=confidence,
        condition=" ".join(conditions) or None,
        warnings=tuple(dict.fromkeys(warnings)),
        kind=spec.kind,
        diptote=spec.diptote if spec.kind is PluralKind.BROKEN else False,
    )
