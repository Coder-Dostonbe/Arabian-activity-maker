"""Single entry point for form generation, used by the CLI and (later) the API."""

from __future__ import annotations

from .dual import generate_dual
from .lexicon import Lexicon
from .plural import generate_plural
from .singular import generate_singular
from .types import Case, GenerationResult, Number, PluralKind


def generate(
    word: str,
    number: Number,
    case: Case = Case.NOMINATIVE,
    *,
    definite: bool | None = None,
    construct: bool = False,
    kind: PluralKind | None = None,
    lexicon: Lexicon | None = None,
) -> GenerationResult:
    if kind is not None and number is not Number.PLURAL:
        raise ValueError("a plural kind can only be given with Number.PLURAL")
    common = dict(definite=definite, construct=construct, lexicon=lexicon)
    if number is Number.SINGULAR:
        return generate_singular(word, case, **common)
    if number is Number.DUAL:
        return generate_dual(word, case, **common)
    return generate_plural(word, case, kind=kind, **common)


def paradigm(word: str, number: Number, *, kind: PluralKind | None = None,
             lexicon: Lexicon | None = None) -> dict[str, dict[str, GenerationResult]]:
    """All three cases for the indefinite, definite and construct states."""
    states = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}
    return {
        state: {c.value: generate(word, number, c, definite=d, construct=k, kind=kind, lexicon=lexicon)
                for c in Case}
        for state, (d, k) in states.items()
    }
