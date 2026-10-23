"""Steps shared by every generator: parse → validate → interpret → assemble."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .classify import Interpretation, interpret
from .lexicon import Lexicon
from .noun_input import InputError, ParsedNoun, parse_noun
from .types import GeneratedForm, GenerationResult, Status

ASSUMPTIONS = (
    "The input is treated as a singular noun or adjective; part of speech is not verified.",
    "The case comes from the request; sentence context is not analysed here.",
)


@lru_cache(maxsize=1)
def default_lexicon() -> Lexicon:
    return Lexicon.seed()


@dataclass
class Prepared:
    parsed: ParsedNoun
    definite: bool
    interpretations: list[Interpretation]
    warnings: list[str]
    lexicon: Lexicon


def error(word: str, message: str, warnings=()) -> GenerationResult:
    return GenerationResult(
        input=word, status=Status.ERROR, errors=(message,),
        warnings=tuple(dict.fromkeys(warnings)), assumptions=ASSUMPTIONS,
    )


def prepare(word: str, *, definite: bool | None, construct: bool,
            lexicon: Lexicon | None) -> Prepared | GenerationResult:
    lexicon = default_lexicon() if lexicon is None else lexicon
    try:
        parsed = parse_noun(word)
    except InputError as exc:
        return error(word, str(exc))
    definite = parsed.definite if definite is None else definite
    warnings = list(parsed.warnings)
    if construct and definite:
        return error(
            word,
            "A noun in the construct state does not take ال (genuine iḍāfa); "
            "the non-genuine annexation of adjectives (الضاربا زيدٍ) is not supported yet.",
            warnings,
        )
    interpretations, more = interpret(parsed, lexicon)
    warnings.extend(more)
    if not interpretations:
        return error(word, "The word could not be classified.", warnings)
    return Prepared(parsed, definite, interpretations, warnings, lexicon)


def finish(word: str, forms: list[GeneratedForm], warnings: list[str], ambiguous: bool,
           empty_message: str) -> GenerationResult:
    if not forms:
        return error(word, empty_message, warnings)
    if len(forms) > 1 and len({f.text for f in forms}) == 1:
        if len({f.vocalized for f in forms}) == 1:
            warnings.append("Several readings are possible (see each form's condition), "
                            "but they produce the same written form.")
            ambiguous = False
        else:
            warnings.append("The readings share a written form but differ in vocalisation.")
    return GenerationResult(
        input=word,
        status=Status.AMBIGUOUS if ambiguous else Status.OK,
        forms=tuple(forms),
        warnings=tuple(dict.fromkeys(warnings)),
        assumptions=ASSUMPTIONS,
    )
