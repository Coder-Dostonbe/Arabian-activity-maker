"""Linguistic regression tests driven by every file in tests/corpus/.

Each corpus file declares a `number` (singular / dual / plural). Each case lists
the acceptable written forms per grammatical case (`expected`), optionally the
exact vocalised forms (`expected_vocalized`), or a subset that must appear
(`expected_includes`) for ambiguous inputs.
"""

import json
import unicodedata
from pathlib import Path

import pytest

from arabmorph import RULES, Case, Lexicon, Number, PluralKind, Source, Status, generate, generate_in_context

CORPUS_DIR = Path(__file__).parent / "corpus"
CORPORA = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(CORPUS_DIR.glob("*.json"))}
CASES = [(name, corpus, item) for name, corpus in CORPORA.items() for item in corpus["cases"]]
SEED = Lexicon.seed()
EMPTY = Lexicon.empty()

STATES = {
    "indefinite": {"definite": False, "construct": False},
    "definite": {"definite": True, "construct": False},
    "construct": {"definite": False, "construct": True},
    "input": {"definite": None, "construct": False},
}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def _run(corpus, item, case):
    common = dict(
        kind=PluralKind(item["kind"]) if item.get("kind") else None,
        lexicon=SEED if item["lexicon"] == "seed" else EMPTY,
        **STATES[item["state"]],
    )
    if "preceding" in item:
        # The case comes from the context; the corpus key states which case is expected.
        result = generate_in_context(item["word"], Number(item.get("number", corpus["number"])),
                                     item["preceding"], **common)
        assert all(f.case is case for f in result.forms), (case, result.to_dict())
        return result
    return generate(item["word"], Number(corpus["number"]), case, **common)


def _case_names(item):
    names = {}
    for key in ("expected", "expected_vocalized", "expected_includes"):
        names.update(item.get(key) or {})
    return list(names) or ["nominative"]


@pytest.mark.parametrize("name,corpus,item", CASES, ids=[f"{n}:{i['id']}" for n, _, i in CASES])
def test_corpus_case(name, corpus, item):
    for case_name in _case_names(item):
        result = _run(corpus, item, Case(case_name))
        info = (case_name, result.to_dict())
        assert result.status == Status(item["status"]), info
        if result.status is Status.ERROR:
            continue
        texts = {f.text for f in result.forms}
        if case_name in item.get("expected", {}):
            assert texts == set(item["expected"][case_name]), info
        if case_name in item.get("expected_vocalized", {}):
            assert {f.vocalized for f in result.forms} == {nfc(v) for v in item["expected_vocalized"][case_name]}, info
        if case_name in item.get("expected_includes", {}):
            assert set(item["expected_includes"][case_name]) <= texts, info
        assert any(item["rule"] in f.rule_ids for f in result.forms), info
        if item.get("source"):
            assert all(f.source is Source(item["source"]) for f in result.forms), info


def test_corpus_entries_are_well_formed():
    for name, corpus in CORPORA.items():
        assert corpus["number"] in {n.value for n in Number}, name
        ids = [c["id"] for c in corpus["cases"]]
        assert len(ids) == len(set(ids)), f"duplicate ids in {name}"
        for c in corpus["cases"]:
            where = f"{name}:{c['id']}"
            assert c["ref"] in corpus["references"], where
            assert c["state"] in STATES, where
            if c["status"] == "error":
                assert "rule" not in c, where
                continue
            assert c["rule"] in RULES, where
            assert c.get("expected") or c.get("expected_vocalized") or c.get("expected_includes"), where


def test_every_rule_is_covered_by_some_corpus():
    covered = {c["rule"] for _, _, c in CASES if "rule" in c}
    assert set(RULES) - covered == set()
