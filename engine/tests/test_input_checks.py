"""Input normalisation, rejected inputs, duplicate forms and "did you mean" suggestions."""

import pytest

from arabmorph import Case, Lexicon, Number, Status, case_from_context, generate, generate_in_context


def _same(a, b):
    """Two results agree on everything the user sees except warnings about the spelling."""
    da, db = a.to_dict(), b.to_dict()
    for d in (da, db):
        d.pop("input"), d.pop("warnings")
    return da == db


@pytest.mark.parametrize("variant,standard", [
    ("مستشفی", "مستشفى"),   # Persian ی, final: the lexicon has the ى spelling
    ("كتابی", "كتابي"),     # Persian ی, final: no ى entry, so it stays ي
    ("ﻛﺘﺎﺏ", "كتاب"),       # presentation forms
    ("کتاب", "كتاب"),       # Persian ک
])
@pytest.mark.parametrize("number", list(Number))
def test_spelling_variants_give_the_standard_result(variant, standard, number):
    assert _same(generate(variant, number), generate(standard, number))


def test_every_substitution_is_a_warning_and_the_input_is_kept():
    r = generate("مستشفی", Number.DUAL)
    assert r.input == "مستشفی"
    assert any("U+06CC" in w for w in r.warnings)
    assert any("read as ى" in w for w in r.warnings)
    r = generate("ﻛﺘﺎﺏ", Number.DUAL)
    assert any("presentation forms" in w for w in r.warnings)


def test_quranic_marks_are_stripped_with_a_warning():
    r = generate("كِتَابٌ" + chr(0x06D6), Number.DUAL)
    assert r.status is Status.OK
    assert any("U+06D6" in w for w in r.warnings)


def test_identical_readings_are_merged_into_one_form():
    r = generate("مستشفي", Number.DUAL, lexicon=Lexicon.empty())
    assert len(r.forms) == 1
    form = r.forms[0]
    assert {"dual.manqus", "dual.sound"} <= set(form.rule_ids)
    assert "Or:" in form.condition
    assert any("same written form" in w for w in r.warnings)


def test_clitic_error_suggests_the_bare_word():
    r = generate("بالكتاب", Number.SINGULAR)
    assert r.status is Status.ERROR and r.forms == ()
    assert r.suggestions == ("كتاب", "الكتاب")
    assert "كتاب" in r.errors[0]


def test_already_dual_names_the_singular():
    r = generate("كتابان", Number.DUAL)
    assert r.status is Status.ERROR
    assert "dual of «كتاب»" in r.errors[0]
    assert r.suggestions == ("كتاب",)


def test_dual_looking_word_without_lexicon_is_ambiguous_and_keeps_the_warning():
    r = generate("إنسان", Number.DUAL)
    assert r.status is Status.AMBIGUOUS
    assert any("ends like a dual or plural" in w for w in r.warnings)


def test_attested_plural_comes_first_and_the_analogical_one_is_marked():
    r = generate("سماء", Number.PLURAL)
    primary, analogical = r.forms
    assert primary.text == "سماوات" and "plural.fem.attested_form" in primary.rule_ids
    assert any("سموات" in w for w in primary.warnings)
    assert analogical.text == "سماءات"
    assert analogical.confidence < primary.confidence
    assert "rarely used" in analogical.condition


def test_five_noun_construct_explains_the_speaker_yeh():
    r = generate("أب", Number.SINGULAR, Case.GENITIVE, construct=True)
    assert r.forms[0].vocalized == "أَبِي"
    assert "ـي" in r.forms[0].condition


def test_five_nouns_have_no_sound_plural():
    r = generate("أب", Number.PLURAL, kind=None)
    assert all(f.text == "آباء" for f in r.forms)


@pytest.mark.parametrize("typed,meant", [("إسم", "اسم"), ("مستشفي", "مستشفى")])
def test_did_you_mean_suggests_but_never_substitutes(typed, meant):
    r = generate(typed, Number.DUAL)
    assert meant in r.suggestions
    assert r.to_dict()["suggestions"] == list(r.suggestions)
    assert all(not f.text.startswith(meant) for f in r.forms)


def test_hamzaless_ila_as_noun_is_an_error_with_suggestion():
    r = generate("الى", Number.DUAL)
    assert r.status is Status.ERROR
    assert r.suggestions == ("إلى",)


def test_no_suggestions_for_a_lexicon_word():
    assert generate("كتاب", Number.DUAL).suggestions == ()


# --- context ---------------------------------------------------------------------

def test_hamzaless_an_suggests_inna_and_anna():
    ctx = case_from_context("ان")
    assert ctx.case is None
    assert ctx.suggestions == ("إنّ", "أنّ")
    r = generate_in_context("الطالب", Number.SINGULAR, "ان")
    assert r.suggestions == ("إنّ", "أنّ")


def test_adverb_assumes_mudaf_ilayh():
    r = generate_in_context("الدرس", Number.SINGULAR, "بعد")
    assert r.forms[0].case is Case.GENITIVE
    assert any("muḍāf ilayh" in w for w in r.forms[0].warnings)


def test_second_person_reading_of_takun_is_flagged():
    ctx = case_from_context("تكون")
    assert ctx.case is Case.NOMINATIVE
    assert any("second person" in w for w in ctx.warnings)


def test_la_nafiya_fem_plural_mentions_the_fatha_alternative():
    r = generate_in_context("معلمة", Number.PLURAL, "لا", definite=False)
    assert any("لا طالباتَ" in w for w in r.forms[0].warnings)
    assert "ً" not in r.forms[0].vocalized and "ٍ" not in r.forms[0].vocalized
