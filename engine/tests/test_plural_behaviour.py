"""Behavioural tests for plurals, declension and the unified API."""

import json
import unicodedata

import pytest

from arabmorph import Case, Lexicon, Number, PluralKind, Source, Status, generate, generate_plural
from arabmorph.__main__ import main


def nfc(s):
    return unicodedata.normalize("NFC", s)


def lexicon(*entries):
    return Lexicon.from_json(json.dumps({"package": "test", "version": "0", "entries": list(entries)}))


def test_asserted_plural_is_capped_and_labelled():
    r = generate_plural("كاتب", kind=PluralKind.SOUND_MASCULINE, lexicon=Lexicon.empty())
    f = r.forms[0]
    assert f.source is Source.ASSERTED
    assert f.confidence <= 0.6
    assert "asserted" in f.condition


def test_heuristic_feminine_candidate_is_low_confidence_and_explained():
    r = generate_plural("حديقة", lexicon=Lexicon.empty())
    assert r.status is Status.AMBIGUOUS
    assert r.forms[0].confidence <= 0.4
    assert "broken" in r.forms[0].condition


def test_broken_plural_is_never_derived_without_lexicon():
    r = generate_plural("كاتب", kind=PluralKind.BROKEN, lexicon=Lexicon.empty())
    assert r.status is Status.ERROR
    assert any("only from lexicon" in w for w in r.warnings)


def test_kind_filters_recorded_plurals():
    r = generate_plural("شجرة", kind=PluralKind.BROKEN)
    assert [f.text for f in r.forms] == ["أشجار"]
    assert r.forms[0].kind is PluralKind.BROKEN


def test_itbaa_skipped_for_adjectives():
    lex = lexicon({"id": "t1", "lemma": "ضَخْمَة", "pos": "adjective", "gender": "feminine",
                   "final_class": "sound", "plurals": [{"kind": "sound_feminine"}]})
    r = generate_plural("ضخمة", lexicon=lex)
    assert r.forms[0].vocalized == nfc("ضَخْمَاتٌ")
    assert "plural.fem.itbaa" not in r.forms[0].rule_ids


def test_fu3la_nouns_warn_about_alternative_vocalisations():
    r = generate_plural("غرفة", kind=PluralKind.SOUND_FEMININE)
    assert any("غُرُفات" in w for w in r.forms[0].warnings)


def test_masculine_plural_of_feminine_mamdud_is_unsupported():
    r = generate_plural("حمراء", kind=PluralKind.SOUND_MASCULINE)
    assert r.status is Status.ERROR
    assert "not supported" in r.errors[0]


def test_masculine_plural_of_feminine_entry_warns():
    lex = lexicon({"id": "t1", "lemma": "شَمْس", "pos": "noun", "gender": "feminine", "final_class": "sound"})
    r = generate_plural("شمس", kind=PluralKind.SOUND_MASCULINE, lexicon=lex)
    assert any("feminine" in w for w in r.forms[0].warnings)


def test_entry_without_recorded_plural_is_reported():
    r = generate_plural("هدى")
    assert r.status is Status.ERROR
    assert any("No plural is recorded" in w for w in r.warnings)


def test_broken_plural_without_form_is_rejected():
    with pytest.raises(ValueError):
        lexicon({"id": "t1", "lemma": "قَلَم", "pos": "noun", "final_class": "sound",
                 "plurals": [{"kind": "broken"}]})


def test_duplicate_lexicon_ids_are_rejected():
    e = {"id": "t1", "lemma": "قَلَم", "pos": "noun", "final_class": "sound"}
    with pytest.raises(ValueError):
        lexicon(e, e)


def test_kind_only_with_plural():
    with pytest.raises(ValueError):
        generate("كتاب", Number.DUAL, kind=PluralKind.BROKEN)


def test_construct_with_article_rejected_for_every_number():
    for n in Number:
        assert generate("الكتاب", n, construct=True).status is Status.ERROR


def test_singular_unknown_noun_warns_about_diptote_assumption():
    r = generate("حديقة", Number.SINGULAR, lexicon=Lexicon.empty())
    assert any("diptote" in w for w in r.forms[0].warnings)


def test_cli_outputs_json(capsys):
    assert main(["plural", "مهندس", "--case", "accusative"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["forms"][0]["text"] == "مهندسين"
    assert out["forms"][0]["kind"] == "sound_masculine"


def test_cli_after(capsys):
    assert main(["plural", "مدرسة", "--after", "في", "--definite", "--kind", "broken"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["forms"][0]["vocalized"] == nfc("الْمَدَارِسِ")


def test_cli_paradigm(capsys):
    assert main(["singular", "أحمد", "--all"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert set(out) == {"indefinite", "definite", "construct"}
    assert out["indefinite"]["genitive"]["forms"][0]["vocalized"] == nfc("أَحْمَدَ")
