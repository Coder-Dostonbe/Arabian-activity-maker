"""Lexicon files: schema validation, the importer, loading several files, and load time."""

import copy
import importlib.util
import json
import time
from importlib import resources
from pathlib import Path

import pytest

from arabmorph import Case, Lexicon, Number, Status, generate
from arabmorph.lexicon import validate_document
from arabmorph.pipeline import default_lexicon

ENGINE = Path(__file__).resolve().parents[1]
SAMPLE = ENGINE / "scripts" / "sample_lexicon.tsv"
LOAD_BUDGET = 0.3   # seconds, for every bundled lexicon file


def _importer():
    spec = importlib.util.spec_from_file_location("import_lexicon", ENGINE / "scripts" / "import_lexicon.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_doc() -> dict:
    return json.loads(resources.files("arabmorph.data").joinpath("lexicon_seed.json").read_text(encoding="utf-8"))


def _sample_lexicon(tmp_path) -> Lexicon:
    out = tmp_path / "lexicon_sample.json"
    assert _importer().main([str(SAMPLE), "--format", "tsv", "--source", "sample", "--version", "0.1",
                             "--license", "CC0-1.0", "-o", str(out)]) == 0
    return Lexicon.from_json(out.read_text(encoding="utf-8"))


# --- every entry works ------------------------------------------------------------

def _all_entries():
    return list(default_lexicon())


@pytest.mark.parametrize("entry", _all_entries(), ids=lambda e: e.id)
def test_every_bundled_entry_declines_dualises_and_pluralises(entry):
    _check_entry(entry, default_lexicon())


def test_every_sample_entry_declines_dualises_and_pluralises(tmp_path):
    lex = _sample_lexicon(tmp_path)
    for entry in lex:
        _check_entry(entry, lex)


def _check_entry(entry, lex):
    """No internal error and a form for every case and state; plurals only when recorded."""
    for number in Number:
        if number is Number.PLURAL and not entry.plurals:
            continue
        for case in Case:
            for definite, construct in ((False, False), (True, False), (False, True)):
                if construct and entry.pos == "proper_noun":
                    continue
                r = generate(entry.lemma, number, case, definite=definite, construct=construct, lexicon=lex)
                assert r.status is not Status.ERROR or _expected_gap(entry, number, construct), \
                    (entry.id, number, case, definite, construct, r.errors)


def _expected_gap(entry, number, construct) -> bool:
    # Proper nouns and five nouns have documented unsupported combinations; nothing else may fail.
    return entry.pos == "proper_noun" or (entry.five_noun and number is Number.PLURAL)


# --- schema ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(f.name for f in resources.files("arabmorph.data").iterdir()
                                         if f.name.startswith("lexicon_") and f.name.endswith(".json")))
def test_every_bundled_file_is_valid_and_unverified(name):
    doc = json.loads(resources.files("arabmorph.data").joinpath(name).read_text(encoding="utf-8"))
    assert validate_document(doc, allow_verified=False) == []


@pytest.mark.parametrize("mutate,problem", [
    (lambda d: d["entries"].append(copy.deepcopy(d["entries"][0])), "duplicate id"),
    (lambda d: d["entries"][0].update(final_class="weak"), "invalid final_class"),
    (lambda d: d["entries"][0].update(gender="neuter"), "invalid gender"),
    (lambda d: d["entries"][0].update(pos="verb"), "invalid pos"),
    (lambda d: d["entries"][15]["plurals"][0].update(form="كتب"), "is not vocalised"),
    (lambda d: d["entries"][15]["plurals"][0].pop("form"), "needs an explicit form"),
    (lambda d: d["entries"][15]["plurals"][0].update(kind="paucal"), "plural 0"),
    (lambda d: d["entries"][0].update(lemma="عصا"), "lemma is not vocalised"),
    (lambda d: d["entries"][0].update(lemma="book"), "not a single Arabic word"),
    (lambda d: d["entries"][0].update(colour="red"), "unknown field 'colour'"),
    (lambda d: d["entries"][0].pop("final_class"), "'final_class' is required"),
    (lambda d: d.pop("version"), "missing 'version'"),
])
def test_validation_reports_each_problem(mutate, problem):
    doc = _seed_doc()
    mutate(doc)
    problems = validate_document(doc)
    assert any(problem in p for p in problems), problems


def test_imported_entries_may_not_be_verified():
    doc = _seed_doc()
    doc["entries"][0]["verified"] = True
    assert validate_document(doc) == []
    assert any("verified" in p for p in validate_document(doc, allow_verified=False))


# --- importer ---------------------------------------------------------------------------

def test_import_tags_every_entry_and_never_verifies(tmp_path):
    lex = _sample_lexicon(tmp_path)
    assert len(lex) == 8
    assert all(e.source == "sample@0.1" and not e.verified and e.id.startswith("sample-") for e in lex)
    doc = json.loads((tmp_path / "lexicon_sample.json").read_text(encoding="utf-8"))
    assert doc["license"] == "CC0-1.0"
    assert validate_document(doc, allow_verified=False) == []


def test_imported_broken_plural_and_diptote_are_used(tmp_path):
    lex = _sample_lexicon(tmp_path)
    r = generate("مفتاح", Number.PLURAL, Case.GENITIVE, lexicon=lex)
    assert r.status is Status.OK
    assert [f.vocalized for f in r.forms] == ["مَفَاتِيحَ"]


def test_invalid_rows_fail_the_import_and_write_nothing(tmp_path, capsys):
    bad = tmp_path / "bad.tsv"
    bad.write_text(SAMPLE.read_text(encoding="utf-8")
                   + "9\tكتاب\tnoun\tmasculine\tsound\t-\t-\t-\tbroken:كتب\tbook\n"
                   + "1\tنَجْم\tnoun\tmasculine\tsound\t-\t-\t-\t-\tstar\n"
                   + "10\tقَلَم\tnoun\n", encoding="utf-8")
    out = tmp_path / "lexicon_bad.json"
    args = [str(bad), "--format", "tsv", "--source", "bad", "--version", "1", "--license", "x", "-o", str(out)]
    assert _importer().main(args) == 1
    assert not out.exists()
    err = capsys.readouterr().err
    assert "line 11" in err and "lemma is not vocalised" in err
    assert "line 12" in err and "duplicate id bad-1" in err
    assert "line 13" in err and "expected 10 columns" in err

    assert _importer().main(args + ["--skip-invalid"]) == 0
    assert len(Lexicon.from_json(out.read_text(encoding="utf-8"))) == 8


def test_import_refuses_ids_already_in_another_file(tmp_path, capsys):
    _sample_lexicon(tmp_path)
    copy_ = tmp_path / "lexicon_sample_copy.json"
    importer = _importer()
    args = [str(SAMPLE), "--format", "tsv", "--source", "sample", "--version", "0.2", "--license", "x",
            "-o", str(copy_)]
    assert importer.main(args) == 1
    assert "already in another lexicon file" in capsys.readouterr().err


# --- loading several files --------------------------------------------------------

def test_files_load_together_seed_first(tmp_path):
    _sample_lexicon(tmp_path)
    (tmp_path / "lexicon_seed.json").write_text(json.dumps(_seed_doc(), ensure_ascii=False), encoding="utf-8")
    lex = Lexicon.from_files(tmp_path.glob("lexicon_*.json"))
    ids = [e.id for e in lex]
    assert ids[0].startswith("seed-") and ids[-1].startswith("sample-")
    assert lex.lookup("نجم") and lex.lookup("كتاب")


def test_duplicate_ids_across_files_are_rejected(tmp_path):
    for name in ("lexicon_a.json", "lexicon_b.json"):
        (tmp_path / name).write_text(json.dumps(_seed_doc(), ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate lexicon id"):
        Lexicon.from_files(tmp_path.glob("lexicon_*.json"))


def test_bundled_lexicon_loads_within_budget():
    start = time.perf_counter()
    Lexicon.bundled()
    assert time.perf_counter() - start < LOAD_BUDGET


def test_extra_files_load_after_the_bundled_ones(tmp_path):
    _sample_lexicon(tmp_path)
    lex = Lexicon.bundled([tmp_path / "lexicon_sample.json"])
    assert lex.lookup("كتاب") and lex.lookup("نجم")
    assert [e.id for e in lex][-1].startswith("sample-")


def test_default_lexicon_can_be_replaced_and_restored(tmp_path):
    from arabmorph.pipeline import set_default_lexicon
    lex = _sample_lexicon(tmp_path)
    try:
        set_default_lexicon(lex)
        assert generate("نجم", Number.PLURAL).forms[0].text == "نجوم"
        assert default_lexicon() is lex
    finally:
        set_default_lexicon(None)
    assert not default_lexicon().lookup("نجم")
