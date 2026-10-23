"""Context-to-case tests beyond the corpus."""

from arabmorph import Case, Number, case_from_context, generate_in_context


def test_undiacritized_min_is_lower_confidence_with_warning():
    plain = case_from_context("من")
    vocalized = case_from_context("مِنْ")
    assert plain.case is vocalized.case is Case.GENITIVE
    assert plain.confidence < vocalized.confidence
    assert any("مَن" in w for w in plain.warnings)


def test_context_caps_form_confidence_and_records_rule_first():
    r = generate_in_context("كتاب", Number.SINGULAR, "كان")
    f = r.forms[0]
    assert f.rule_ids[0] == "context.kana_nominative"
    assert f.confidence <= 0.7
    assert any("اسم كان" in w for w in f.warnings)


def test_assumptions_name_the_context_word():
    r = generate_in_context("كتاب", Number.SINGULAR, "في")
    assert any("«في»" in a for a in r.assumptions)
    assert not any("case comes from the request" in a for a in r.assumptions)


def test_unrecognised_governor_explains_instead_of_guessing():
    r = generate_in_context("كتاب", Number.SINGULAR, "قرأ")
    assert r.forms == ()
    assert any("syntactic analysis" in w for w in r.warnings)
