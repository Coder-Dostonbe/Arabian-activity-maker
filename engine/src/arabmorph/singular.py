"""Case forms of the singular itself (كتابٌ / كتابًا / كتابٍ …)."""

from __future__ import annotations

from .chars import ALEF, DAMMA, FATHA, KASRA, WAW, YEH
from .classify import Interpretation
from .clusters import Cluster, join_clusters
from .declension import decline
from .lexicon import Lexicon
from .normalize import strip_diacritics
from .orthography import add_article, add_mark
from .pipeline import Prepared, finish, prepare
from .rules import get_rule
from .types import Case, FinalClass, GeneratedForm, GenerationResult, HamzaType, Number


def generate_singular(
    word: str,
    case: Case = Case.NOMINATIVE,
    *,
    definite: bool | None = None,
    construct: bool = False,
    lexicon: Lexicon | None = None,
) -> GenerationResult:
    prep = prepare(word, definite=definite, construct=construct, lexicon=lexicon)
    if not isinstance(prep, Prepared):
        return prep
    definite = prep.definite
    indefinite = not (definite or construct)
    forms: list[GeneratedForm] = []
    ambiguous = len(prep.interpretations) > 1

    for interp in prep.interpretations:
        entry = prep.lexicon.get(interp.entry_id) if interp.entry_id else None
        cls = FinalClass.SOUND if interp.final_class is FinalClass.MAMDUD else interp.final_class
        warnings = list(interp.warnings)

        if entry is not None:
            options = [(entry.diptote or interp.hamza_type is HamzaType.FEMININE, None, 1.0)]
        elif interp.final_class is FinalClass.MAMDUD and interp.hamza_type is None and indefinite:
            options = [
                (True, "If the hamza marks the feminine (like صحراء), the noun is diptote.", 0.55),
                (False, "Otherwise (like سماء) it is fully declinable.", 0.55),
            ]
            ambiguous = True
        else:
            options = [(interp.hamza_type is HamzaType.FEMININE, None, 1.0)]
            if indefinite and cls is not FinalClass.MAQSUR:
                warnings.append("Assumed fully declinable (منصرف); proper names, أفعل adjectives and "
                                "some patterns are diptote.")

        if interp.five_noun and construct:
            forms.append(_five_noun_construct(interp, case))
            continue

        for diptote, condition, factor in options:
            declined = decline(interp.stem, case, definite=definite, construct=construct,
                               diptote=diptote, final_class=cls)
            body = add_article(declined.clusters) if definite else declined.clusters
            vocalized = join_clusters(body)
            conditions = [c for c in (interp.condition, condition) if c]
            forms.append(GeneratedForm(
                text=strip_diacritics(vocalized),
                vocalized=vocalized,
                number=Number.SINGULAR,
                case=case,
                definite=definite,
                construct=construct,
                rule_ids=declined.rule_ids,
                source=interp.source,
                confidence=round(min(interp.confidence, get_rule(declined.rule_ids[0]).confidence) * factor, 2),
                condition=" ".join(conditions) or None,
                warnings=tuple(dict.fromkeys(warnings)),
                diptote=diptote,
            ))

    return finish(word, forms, prep.warnings, ambiguous, "No declension rule applies to this word.", prep=prep)


_FIVE_NOUN_ENDINGS = {Case.NOMINATIVE: (DAMMA, WAW), Case.ACCUSATIVE: (FATHA, ALEF), Case.GENITIVE: (KASRA, YEH)}


def _five_noun_construct(interp: Interpretation, case: Case) -> GeneratedForm:
    """أبو زيدٍ / أبا زيدٍ / أبي زيدٍ: in the construct state the five nouns decline with letters."""
    vowel, letter = _FIVE_NOUN_ENDINGS[case]
    stem = list(interp.stem)
    stem[-1] = add_mark(stem[-1], vowel)
    vocalized = join_clusters(stem + [Cluster(letter)])
    return GeneratedForm(
        text=strip_diacritics(vocalized),
        vocalized=vocalized,
        number=Number.SINGULAR,
        case=case,
        definite=False,
        construct=True,
        rule_ids=("decl.five_nouns",),
        source=interp.source,
        confidence=round(min(interp.confidence, get_rule("decl.five_nouns").confidence), 2),
        condition="If the following genitive is a noun or a pronoun other than the speaker's ـي "
                  "(أبوك، أبو زيدٍ); with ـي (أبي = my father) the ending is implicit.",
        warnings=interp.warnings,
        diptote=False,
    )
