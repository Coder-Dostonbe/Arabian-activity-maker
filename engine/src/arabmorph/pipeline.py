"""Steps shared by every generator: parse → validate → interpret → assemble."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache

from .chars import ALEF_MAQSURA, TEH_MARBUTA, YEH
from .classify import Interpretation, interpret
from .clusters import Cluster, bare
from .function_words import PARTICLES
from .lexicon import Lexicon, LexiconEntry
from .noun_input import InputError, ParsedNoun, parse_noun
from .normalize import lossy_key
from .types import GeneratedForm, GenerationResult, Status

ASSUMPTIONS = (
    "The input is treated as a singular noun or adjective; part of speech is not verified.",
    "The case comes from the request; sentence context is not analysed here.",
)

CLITICS = "بلكوف"          # بـ لـ كـ وـ فـ written joined to the next word
DUAL_ENDINGS = ("ان",)
DUAL_OR_PLURAL_ENDINGS = ("ين",)
PLURAL_ENDINGS = ("ون", "ات")
# Five nouns typed in their construct forms (أبو / أبا / أبي …), and ذو / فو, which never stand alone.
FIVE_NOUN_CONSTRUCT_LETTERS = "واي"
CONSTRUCT_ONLY = {
    "ذو": "ذو (ذا، ذي) is used only in the construct state (ذو علمٍ); it has no stand-alone singular "
          "to inflect, and its dual (ذوا / ذوي) and plural (ذوو / ذوي) are not supported yet.",
    "فو": "فو (فا، في) is the construct form of فم used only before a noun (فو زيدٍ); enter فم instead.",
}


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
    suggestions: tuple[str, ...] = ()
    uncertain_input: bool = False   # the input may not be singular; never report a clean ok


def error(word: str, message: str, warnings=(), suggestions=()) -> GenerationResult:
    return GenerationResult(
        input=word, status=Status.ERROR, errors=(message,),
        warnings=tuple(dict.fromkeys(warnings)), assumptions=ASSUMPTIONS,
        suggestions=tuple(dict.fromkeys(suggestions)),
    )


def prepare(word: str, *, definite: bool | None, construct: bool,
            lexicon: Lexicon | None) -> Prepared | GenerationResult:
    lexicon = default_lexicon() if lexicon is None else lexicon
    try:
        parsed = parse_noun(word)
    except InputError as exc:
        return error(word, str(exc))
    parsed = _resolve_final_yeh(parsed, lexicon)
    warnings = list(parsed.warnings)

    rejected = _reject(parsed, lexicon)
    if rejected:
        message, suggestions = rejected
        return error(word, message, warnings, suggestions)
    uncertain_input = _looks_inflected(parsed, lexicon)
    suggestions = _suggestions(parsed, lexicon)
    if suggestions:
        warnings.append("The lexicon has no entry for this spelling. Did you mean "
                        + " / ".join(f"«{s}»" for s in suggestions) + "? The input was not changed.")

    definite = parsed.definite if definite is None else definite
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
        return error(word, "The word could not be classified.", warnings, suggestions)
    return Prepared(parsed, definite, interpretations, warnings, lexicon, suggestions, uncertain_input)


def finish(word: str, forms: list[GeneratedForm], warnings: list[str], ambiguous: bool,
           empty_message: str, *, prep: Prepared | None = None) -> GenerationResult:
    suggestions = prep.suggestions if prep else ()
    if not forms:
        return error(word, empty_message, warnings, suggestions)
    readings = len(forms)
    forms = merge_duplicates(forms)
    if readings > 1 and len(forms) == 1:
        warnings.append("Several readings are possible (see the form's condition), "
                        "but they produce the same written form.")
        ambiguous = False
    elif len(forms) > 1 and len({f.text for f in forms}) == 1:
        warnings.append("The readings share a written form but differ in vocalisation.")
    if prep is not None and prep.uncertain_input:
        ambiguous = True
    return GenerationResult(
        input=word,
        status=Status.AMBIGUOUS if ambiguous else Status.OK,
        forms=tuple(forms),
        warnings=tuple(dict.fromkeys(warnings)),
        assumptions=ASSUMPTIONS,
        suggestions=suggestions,
    )


def merge_duplicates(forms: list[GeneratedForm]) -> list[GeneratedForm]:
    """One form per vocalisation; readings that produced it are joined, not repeated."""
    merged: dict[str, GeneratedForm] = {}
    for f in forms:
        g = merged.get(f.vocalized)
        if g is None:
            merged[f.vocalized] = f
            continue
        # The merged form holds under either reading; an unconditional reading makes it unconditional.
        if g.condition and f.condition and g.condition != f.condition:
            condition = f"{g.condition} Or: {f.condition}"
        else:
            condition = g.condition if f.condition else None
        merged[f.vocalized] = replace(
            g,
            rule_ids=tuple(dict.fromkeys(g.rule_ids + f.rule_ids)),
            confidence=max(g.confidence, f.confidence),
            condition=condition,
            warnings=tuple(dict.fromkeys(g.warnings + f.warnings)),
        )
    return list(merged.values())


# --- input checks ---------------------------------------------------------------

def _resolve_final_yeh(parsed: ParsedNoun, lexicon: Lexicon) -> ParsedNoun:
    """A word-final Persian ی is ي by default, ى when only that spelling is in the lexicon."""
    stem = parsed.stem
    if not parsed.final_persian_yeh or stem[-1].base != YEH:
        return parsed
    key = bare(stem)
    with_maqsura = key[:-1] + ALEF_MAQSURA
    if lexicon.lookup(key) or not lexicon.lookup(with_maqsura):
        return parsed
    return replace(
        parsed,
        stem=stem[:-1] + (Cluster(ALEF_MAQSURA, stem[-1].marks),),
        warnings=parsed.warnings + (
            f"The final ی was read as ى, because the lexicon has «{with_maqsura}» but not «{key}».",),
    )


def _reject(parsed: ParsedNoun, lexicon: Lexicon) -> tuple[str, list[str]] | None:
    """Inputs that are certainly not a bare singular noun: (message, suggestions), else None."""
    key = bare(parsed.stem)
    if lexicon.lookup(key):
        return None
    if not parsed.definite and key in CONSTRUCT_ONLY:
        return CONSTRUCT_ONLY[key], (["فم"] if key == "فو" else [])
    if not parsed.definite and key in PARTICLES:
        # الى → إلى; the hamza-less spelling itself is never suggested.
        standard = [p for p in sorted(PARTICLES)
                    if p != key and not p.startswith("ا") and lossy_key(p) == lossy_key(key)]
        return f"«{key}» is a particle, not a noun, so it has no dual, plural or case forms.", standard

    clitic = _clitic(parsed, lexicon)
    if clitic:
        return clitic

    five = _five_noun_construct(key, lexicon)
    if five:
        return (f"«{key}» is a construct form of «{five.key}» (الأسماء الخمسة: أبو / أبا / أبي). "
                f"Enter «{five.key}» and request the construct state."), [five.key]

    singular = _singular_of_inflected(parsed, lexicon)
    if singular:
        what, entry = singular
        return (f"«{key}» is already the {what} of «{entry.key}»; enter the singular «{entry.key}».",
                [entry.key])
    return None


def _clitic(parsed: ParsedNoun, lexicon: Lexicon) -> tuple[str, list[str]] | None:
    """بالكتاب / للكتاب / وكتاب: a particle written joined to the noun."""
    if parsed.definite:
        return None
    key = bare(parsed.stem)
    if key.startswith("لل") and len(key) >= 5:
        # لِـ + الـ: the alif of the article is dropped (للكتاب = لـ + الكتاب).
        noun = key[2:]
        return _clitic_message(key, "لـ", "ال" + noun, noun)
    if key[0] not in CLITICS or len(key) < 3:
        return None
    rest = key[1:]
    if rest.startswith("ال") and len(rest) >= 5:
        return _clitic_message(key, key[0] + "ـ", rest, rest[2:])
    if lexicon.lookup(rest):
        return _clitic_message(key, key[0] + "ـ", rest, rest)
    return None


def _clitic_message(key: str, clitic: str, attached: str, noun: str) -> tuple[str, list[str]]:
    return (f"«{key}» looks like the particle {clitic} joined to «{attached}». Enter the noun on its own "
            f"(«{noun}», or «ال{noun}» for the definite form); if «{key}» is itself one word, "
            "it needs a lexicon entry.", [noun, "ال" + noun] if noun != attached else [noun])


def _five_noun_construct(key: str, lexicon: Lexicon) -> LexiconEntry | None:
    if len(key) != 3 or key[-1] not in FIVE_NOUN_CONSTRUCT_LETTERS:
        return None
    return next((e for e in lexicon.lookup(key[:-1]) if e.five_noun), None)


def _singular_candidates(key: str) -> list[tuple[str, str]]:
    """(what, singular spelling) pairs that `key` could be the dual or plural of."""
    ending = key[-2:]
    if ending in DUAL_ENDINGS:
        what = "dual"
    elif ending in DUAL_OR_PLURAL_ENDINGS:
        what = "dual or plural"
    elif ending in PLURAL_ENDINGS:
        what = "plural"
    else:
        return []
    base = key[:-2]
    if len(base) < 2:
        return []
    found = [base]
    last = base[-1]
    if last == "ت":
        found.append(base[:-1] + TEH_MARBUTA)            # شجرتان ← شجرة
    if ending == "ات":
        found.append(base + TEH_MARBUTA)                 # شجرات ← شجرة
        if last in "وي":
            found.append(base[:-1] + "ا" + TEH_MARBUTA)  # صلوات ← صلاة، فتيات ← فتاة
    if last == "ي":
        found += [base[:-1] + ALEF_MAQSURA]              # مستشفيان ← مستشفى
    if last == "و":
        found += [base[:-1] + "ا", base[:-1] + "ء", base[:-1]]   # عصوان، صحراوان، أبوان
    if last == "ئ":
        found.append(base[:-1] + "ء")                    # شيئان ← شيء
    if ending in ("ون", "ين"):
        found += [base + YEH, base + ALEF_MAQSURA]       # محامون ← محامي، مصطفون ← مصطفى
    return [(what, s) for s in dict.fromkeys(found)]


def _singular_of_inflected(parsed: ParsedNoun, lexicon: Lexicon) -> tuple[str, LexiconEntry] | None:
    key = bare(parsed.stem)
    plural_of = lexicon.singulars_of(key)
    if plural_of:
        return "plural", plural_of[0]
    if len(parsed.stem) < 4:
        return None
    for what, singular in _singular_candidates(key):
        entries = lexicon.lookup(singular)
        if entries:
            return what, entries[0]
    return None


def _looks_inflected(parsed: ParsedNoun, lexicon: Lexicon) -> bool:
    """Ends like a dual/plural and the lexicon cannot confirm it is a singular."""
    key = bare(parsed.stem)
    return (len(parsed.stem) >= 4 and key.endswith(DUAL_ENDINGS + DUAL_OR_PLURAL_ENDINGS + PLURAL_ENDINGS)
            and not lexicon.lookup(key))


def _suggestions(parsed: ParsedNoun, lexicon: Lexicon) -> tuple[str, ...]:
    key = bare(parsed.stem)
    if lexicon.lookup(key):
        return ()
    prefix = "ال" if parsed.definite else ""
    words = [prefix + e.key for e in lexicon.lookup_lossy(key) if e.key != key]
    target = lossy_key(prefix + key)
    words += [p for p in sorted(PARTICLES)
              if p != prefix + key and not p.startswith("ا") and lossy_key(p) == target]
    return tuple(dict.fromkeys(words))
