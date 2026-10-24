import json
import sys
import unicodedata
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arabmorph_service as svc  # noqa: E402
from activity import build_items  # noqa: E402
from arabmorph import Case, Number  # noqa: E402


def nfc(s):
    return unicodedata.normalize("NFC", s)


def test_dual_items_have_answer_and_real_distractors():
    r = build_items(["كتاب", "شجرة"], Number.DUAL, Case.NOMINATIVE, "indefinite")
    assert r["skipped"] == []
    book = r["items"][0]
    assert book["prompt"] == "كتاب"
    assert book["answer"] == nfc("كِتَابَانِ")
    assert 1 <= len(book["options"]) <= 3
    assert book["answer"] not in book["options"]
    assert nfc("كِتَابَيْنِ") in book["options"]  # the accusative/genitive dual is the classic confusion


def test_two_valid_forms_are_joined():
    r = build_items(["سماء"], Number.DUAL, Case.NOMINATIVE, "indefinite")
    assert " / " in r["items"][0]["answer"]


def test_ambiguous_and_failing_words_are_skipped_with_reason():
    r = build_items(["مدرسة", "xyz", "", "كتاب", "كتاب"], Number.PLURAL, Case.NOMINATIVE, "indefinite")
    reasons = {s["word"]: s["reason"] for s in r["skipped"]}
    assert reasons["مدرسة"] == "ambiguous"
    assert reasons["xyz"] == "error"
    assert [i["prompt"] for i in r["items"]] == ["كتاب"]  # blanks and duplicates dropped


def test_definite_state():
    r = build_items(["كتاب"], Number.DUAL, Case.GENITIVE, "definite")
    assert r["items"][0]["answer"].startswith(nfc("الْ"))


def test_service_build_items_op():
    r = svc.handle(json.dumps({"id": 1, "op": "build_items",
                               "params": {"words": ["عصا"], "number": "dual", "case": "accusative", "state": "construct"}}))
    assert r["ok"] and r["result"]["items"][0]["prompt"] == "عصا"


@pytest.mark.parametrize("params,needle", [
    ({}, "'words'"),
    ({"words": []}, "'words'"),
    ({"words": ["ك" * 100]}, "at most"),
    ({"words": [3]}, "string"),
    ({"words": ["كتاب"], "state": "vocative"}, "invalid 'state'"),
    ({"words": ["كتاب"], "case": "dative"}, "invalid 'case'"),
])
def test_build_items_validation(params, needle):
    r = svc.handle(json.dumps({"id": 1, "op": "build_items", "params": params}))
    assert not r["ok"] and needle in r["error"]
