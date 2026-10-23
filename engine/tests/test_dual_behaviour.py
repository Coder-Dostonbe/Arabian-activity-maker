"""Behavioural tests of the dual generator beyond the written forms."""

import unicodedata

from arabmorph import Case, Lexicon, Source, Status, generate_dual


def nfc(s):
    return unicodedata.normalize("NFC", s)


def test_vocalized_output_for_vocalized_input():
    nom = generate_dual("كِتَابٌ", Case.NOMINATIVE)
    acc = generate_dual("كِتَابٌ", Case.ACCUSATIVE)
    assert nom.forms[0].vocalized == nfc("كِتَابَانِ")
    assert acc.forms[0].vocalized == nfc("كِتَابَيْنِ")


def test_sun_letter_gets_shadda_and_moon_letter_gets_sukun():
    sun = generate_dual("شَجَرَةٌ", Case.NOMINATIVE, definite=True)
    moon = generate_dual("قَلَمٌ", Case.NOMINATIVE, definite=True)
    assert sun.forms[0].vocalized == nfc("الشَّجَرَتَانِ")
    assert moon.forms[0].vocalized == nfc("الْقَلَمَانِ")


def test_lexicon_supplies_vocalisation_for_bare_input():
    r = generate_dual("مستشفى", Case.NOMINATIVE)
    assert r.forms[0].vocalized == nfc("مُسْتَشْفَيَانِ")
    assert r.forms[0].source is Source.LEXICON


def test_definite_input_can_be_made_indefinite():
    r = generate_dual("الكتاب", Case.NOMINATIVE, definite=False)
    assert [f.text for f in r.forms] == ["كتابان"]


def test_construct_with_article_is_rejected_with_explanation():
    r = generate_dual("الكتاب", Case.NOMINATIVE, construct=True)
    assert r.status is Status.ERROR
    assert r.forms == ()
    assert "construct" in r.errors[0]


def test_construct_accusative_warns_about_kasra_before_wasl():
    r = generate_dual("كتاب", Case.ACCUSATIVE, construct=True)
    assert any("kasra" in w for w in r.forms[0].warnings)


def test_rules_only_maqsur_is_marked_heuristic_with_lower_confidence():
    r = generate_dual("فتى", lexicon=Lexicon.empty())
    form = r.forms[0]
    assert form.source is Source.HEURISTIC
    assert form.confidence < 0.9
    assert form.condition


def test_ambiguous_mamdud_explains_each_alternative():
    r = generate_dual("صحراء", lexicon=Lexicon.empty())
    assert r.status is Status.AMBIGUOUS
    assert all(f.condition for f in r.forms)
    assert all(f.confidence <= 0.6 for f in r.forms)


def test_unreviewed_lexicon_entries_are_flagged():
    r = generate_dual("عصا")
    assert any("not been reviewed" in w for w in r.forms[0].warnings)


def test_several_readings_with_same_written_form_are_reported():
    r = generate_dual("كرسي", lexicon=Lexicon.empty())
    assert r.status is Status.OK
    assert any("same written form" in w for w in r.warnings)


def test_kasratan_on_unknown_faa_pattern_warns_about_dropped_yeh():
    r = generate_dual("رامٍ", lexicon=Lexicon.empty())
    assert any("dropped" in w for w in r.warnings)


def test_possible_dual_input_is_warned():
    r = generate_dual("مهندسون")
    assert any("dual or plural" in w for w in r.warnings)


def test_assumptions_are_always_reported():
    r = generate_dual("كتاب")
    assert r.assumptions and "sentence context" in r.assumptions[1]


def test_invalid_inputs_return_errors_not_forms():
    for bad in ["", "   ", "كتاب جديد", "book", "ك"]:
        r = generate_dual(bad)
        assert r.status is Status.ERROR, bad
        assert r.forms == () and r.errors, bad


def test_result_serialises_to_plain_dict():
    d = generate_dual("سماء").to_dict()
    assert d["status"] == "ok"
    assert len(d["forms"]) == 2
    assert set(d["forms"][0]) >= {"text", "vocalized", "rules", "source", "confidence", "condition", "warnings"}
