import base64
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arabmorph_service as svc  # noqa: E402
import user_lexicon  # noqa: E402
from arabmorph import Number, generate  # noqa: E402
from arabmorph.pipeline import default_lexicon, set_default_lexicon  # noqa: E402
from verify import verify_item  # noqa: E402


def call(op, **params):
    return svc.handle(json.dumps({"id": 1, "op": op, "params": params}))


# --- verifying Claude's items -------------------------------------------------------

@pytest.mark.parametrize("prompt,answer", [
    ("كتاب", "كِتَابَانِ"),
    ("كِتَابٌ", "كُتُبٌ"),
    ("صحراء", "صَحْرَاوَيْنِ"),
    ("مدرسة", "مدارس"),
    ("ما جمع «كتاب»؟", "كُتُبٌ"),       # a question: one of its words explains the answer
])
def test_engine_agrees(prompt, answer):
    assert verify_item(prompt, answer)["status"] == "engine_agrees"


@pytest.mark.parametrize("prompt,answer,engine", [
    ("كتاب", "كتابات", "كُتُبٌ"),              # sound plural for a broken one
    ("صحراء", "صَحْرَاءَانِ", "صَحْرَاوَانِ"),  # hamza left unchanged
    ("كتاب", "كِتَابُونِ", None),               # right word, wrong ending
])
def test_engine_disagrees_and_shows_its_forms(prompt, answer, engine):
    r = verify_item(prompt, answer)
    assert r["status"] == "engine_disagrees"
    assert r["engine"] and answer not in r["engine"]
    if engine:
        assert engine in r["engine"]


@pytest.mark.parametrize("prompt,answer", [
    ("ما جمع كتاب؟", "كتابات"),   # question prompt: the word asked about is not certain
    ("kitob", "kitoblar"),
    ("كتاب", "two books"),
    ("حاسوب", "حواسيب"),           # broken plural of a word the lexicon does not have
])
def test_not_checkable(prompt, answer):
    assert verify_item(prompt, answer)["status"] == "not_checkable"


def test_verify_items_op_validates():
    assert call("verify_items", items=[{"prompt": "كتاب", "answer": "كتابان"}])["result"][0]["status"] == "engine_agrees"
    assert not call("verify_items", items=[])["ok"]
    assert not call("verify_items", items=[{"prompt": "كتاب"}])["ok"]


# --- user lexicon -------------------------------------------------------------------

PROPOSAL = {"lemma": "حَاسُوب", "pos": "noun", "gender": "masculine", "final_class": "sound",
            "alif_origin": "", "hamza_type": "", "diptote": False, "gloss_en": "computer",
            "plurals": [{"kind": "broken", "form": "حَوَاسِيب", "diptote": True}]}


@pytest.fixture
def user_file(tmp_path, monkeypatch):
    path = tmp_path / "lexicon_user.json"
    monkeypatch.setenv(user_lexicon.ENV, str(path))
    yield path
    set_default_lexicon(None)


def test_proposal_is_checked_before_it_is_stored(user_file):
    entry, problems = user_lexicon.check(PROPOSAL)
    assert problems == [] and "alif_origin" not in entry and entry["verified"] is False
    _, problems = user_lexicon.check(dict(PROPOSAL, plurals=[{"kind": "broken", "form": "حواسيب"}]))
    assert any("not vocalised" in p for p in problems)
    assert not user_file.exists()


def test_added_entry_is_used_by_the_engine_and_survives_a_restart(user_file):
    assert generate("حاسوب", Number.PLURAL).status.value == "error"   # no plural is known without a lexicon entry
    r = call("user_lexicon_add", entry=PROPOSAL)
    assert r["ok"], r
    assert r["result"]["entry"]["id"] == "user-0001" and r["result"]["entry"]["source"] == "user"
    assert [f.text for f in generate("حاسوب", Number.PLURAL).forms] == ["حواسيب"]
    assert verify_item("حاسوب", "حَوَاسِيبُ")["status"] == "engine_agrees"

    set_default_lexicon(None)            # a new service process
    assert user_lexicon.load() == []
    assert default_lexicon().lookup("حاسوب")[0].source == "user"
    assert "user" in call("version")["result"]["lexicon_sources"]


def test_remove_and_invalid_entries(user_file):
    call("user_lexicon_add", entry=PROPOSAL)
    assert not call("user_lexicon_add", entry=dict(PROPOSAL, final_class="weak"))["ok"]
    assert call("user_lexicon_remove", id="user-0001")["result"]["removed"] is True
    assert not default_lexicon().lookup("حاسوب")
    assert not call("user_lexicon_remove", id="seed-0001")["ok"]


def test_a_damaged_user_file_is_reported_not_fatal(user_file):
    user_file.write_text("{broken", encoding="utf-8")
    problems = user_lexicon.load()
    assert problems and default_lexicon().lookup("كتاب")


# --- results export -----------------------------------------------------------------

def test_export_xlsx_returns_a_workbook():
    r = call("export_xlsx", sheets={"Natijalar": [["Sana", "Ball"], ["2026-10-29", "8/10"]], "a/b:c": [["x"]]})
    raw = base64.b64decode(r["result"]["data"])
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert "xl/worksheets/sheet2.xml" in z.namelist()
        assert "8/10" in z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert 'name="abc"' in z.read("xl/workbook.xml").decode("utf-8")
    assert not call("export_xlsx", sheets={})["ok"]
