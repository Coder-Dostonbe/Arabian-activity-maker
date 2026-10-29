"""Reverse analysis: a written form back to its singular, number, case and state."""

import json
import subprocess
import sys

import pytest

from arabmorph import Case, Lexicon, Number, PluralKind, Status, analyze, generate, strip_diacritics
from arabmorph.pipeline import default_lexicon

N, A, G = Case.NOMINATIVE, Case.ACCUSATIVE, Case.GENITIVE


def _readings(r):
    return {(strip_diacritics(a.singular), a.number, a.state, a.kind, a.cases) for a in r.analyses}


@pytest.mark.parametrize("word,expected", [
    ("كتب", {("كتاب", Number.PLURAL, "indefinite", PluralKind.BROKEN, (N, G)),
             ("كتاب", Number.PLURAL, "construct", PluralKind.BROKEN, (N, A, G))}),
    ("كتابان", {("كتاب", Number.DUAL, "indefinite", None, (N,))}),
    ("الكتابين", {("كتاب", Number.DUAL, "definite", None, (A, G))}),
    ("معلمون", {("معلم", Number.PLURAL, "indefinite", PluralKind.SOUND_MASCULINE, (N,))}),
    ("معلمو", {("معلم", Number.PLURAL, "construct", PluralKind.SOUND_MASCULINE, (N,))}),
    ("الشجرات", {("شجرة", Number.PLURAL, "definite", PluralKind.SOUND_FEMININE, (N, A, G))}),
    ("مستشفيان", {("مستشفى", Number.DUAL, "indefinite", None, (N,))}),
    ("أبوان", {("أب", Number.DUAL, "indefinite", None, (N,))}),
    ("أبو", {("أب", Number.SINGULAR, "construct", None, (N,))}),
    ("كِتَابًا", {("كتاب", Number.SINGULAR, "indefinite", None, (A,))}),
])
def test_one_lexicon_reading_is_ok(word, expected):
    r = analyze(word)
    assert r.status is Status.OK, r.to_dict()
    assert _readings(r) == expected


def test_attested_plural_finds_the_lemma():
    r = analyze("سماوات")
    assert r.status is Status.OK
    assert {a.singular for a in r.analyses} == {"سَمَاء"}


def test_typed_vowels_narrow_the_case():
    assert {a.cases for a in analyze("كتابٌ").analyses} == {(N,)}
    assert {a.cases for a in analyze("كُتُبٍ").analyses} == {(G,)}


def test_dual_and_plural_readings_are_ambiguous():
    r = analyze("معلمين")
    assert r.status is Status.AMBIGUOUS
    assert {(a.number, a.kind) for a in r.analyses} == {(Number.DUAL, None),
                                                        (Number.PLURAL, PluralKind.SOUND_MASCULINE)}


def test_tanween_alif_or_construct_dual_is_ambiguous():
    r = analyze("كتابا")
    assert r.status is Status.AMBIGUOUS
    assert {(a.number, a.state) for a in r.analyses} == {(Number.SINGULAR, "indefinite"),
                                                         (Number.DUAL, "construct")}


def test_unknown_singulars_are_dropped_when_a_lexicon_word_explains_the_form():
    r = analyze("مستشفيان")
    assert all(a.in_lexicon for a in r.analyses)
    assert any("left out" in w for w in r.warnings)


def test_homograph_broken_plural_names_its_own_lemma():
    r = analyze("مدارس")
    assert {a.singular for a in r.analyses} == {"مَدْرَسَة"}
    assert all(a.entry_id == "seed-0021" for a in r.analyses)


def test_homograph_singular_is_ambiguous():
    r = analyze("مدرسة")
    assert r.status is Status.AMBIGUOUS
    assert any("several words with this spelling" in w for w in r.warnings)


def test_without_lexicon_every_reading_is_kept_and_ambiguous():
    r = analyze("كتابان", lexicon=Lexicon.empty())
    assert r.status is Status.AMBIGUOUS
    assert {(strip_diacritics(a.singular), a.number) for a in r.analyses} >= {
        ("كتاب", Number.DUAL), ("كتابان", Number.SINGULAR)}
    assert not any(a.in_lexicon for a in r.analyses)


def test_clitic_is_an_error_with_suggestions():
    r = analyze("بالكتاب")
    assert r.status is Status.ERROR and r.analyses == ()
    assert r.suggestions == ("كتاب", "الكتاب")


@pytest.mark.parametrize("word", ["", "كتاب قلم", "book"])
def test_bad_input_is_an_error(word):
    assert analyze(word).status is Status.ERROR


def test_to_dict_is_json_ready():
    d = analyze("كتب").to_dict()
    json.dumps(d, ensure_ascii=False)
    assert d["analyses"][0]["kind"] == "broken" and d["analyses"][0]["in_lexicon"] is True


def test_cli_analyze():
    out = subprocess.run([sys.executable, "-m", "arabmorph", "analyze", "كتب"], capture_output=True,
                         check=True).stdout.decode("utf-8")
    assert json.loads(out)["analyses"][0]["singular"] == "كِتَاب"


# --- round trip ------------------------------------------------------------------

STATES = {"indefinite": (False, False), "definite": (True, False), "construct": (False, True)}


def test_every_generated_form_analyses_back_to_its_singular():
    """For each lexicon entry, each form the engine generates is found again by analyze."""
    lex = default_lexicon()
    cache: dict[str, set] = {}
    missing = []
    for entry in lex:
        for number in Number:
            for state, (definite, construct) in STATES.items():
                for case in Case:
                    r = generate(entry.lemma, number, case, definite=definite, construct=construct, lexicon=lex)
                    for f in r.forms:
                        if f.text not in cache:
                            cache[f.text] = {(strip_diacritics(a.singular), a.number, a.state, c)
                                             for a in analyze(f.text, lexicon=lex).analyses for c in a.cases}
                        if (entry.key, number, state, case) not in cache[f.text]:
                            missing.append((entry.id, f.text, number.value, state, case.value))
    assert missing == []
