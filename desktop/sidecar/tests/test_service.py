import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arabmorph_service as svc  # noqa: E402

SERVICE = Path(__file__).resolve().parents[1] / "arabmorph_service.py"


def call(op, **params):
    return svc.handle(json.dumps({"id": 7, "op": op, "params": params}))


def test_generate_dual():
    r = call("generate", word="كتاب", number="dual", case="accusative")
    assert r["ok"] and r["id"] == 7
    assert r["result"]["forms"][0]["text"] == "كتابين"


def test_generate_with_context():
    r = call("generate", word="مدرسة", number="plural", after="في", definite=True, kind="broken")
    assert r["result"]["forms"][0]["case"] == "genitive"


def test_paradigm_has_three_states():
    r = call("paradigm", word="شجرة", number="plural")
    assert set(r["result"]) == {"indefinite", "definite", "construct"}


def test_analyze_returns_the_singular():
    r = call("analyze", word="كتب")
    assert r["ok"] and r["result"]["status"] == "ok"
    a = r["result"]["analyses"][0]
    assert (a["singular"], a["number"], a["kind"]) == ("كِتَاب", "plural", "broken")


@pytest.mark.parametrize("params,needle", [({}, "'word' is required"), ({"word": "ك" * 100}, "at most")])
def test_analyze_validates_the_word(params, needle):
    r = call("analyze", **params)
    assert not r["ok"] and needle in r["error"]


def test_rules_and_lexicon_and_version():
    assert len(call("rules")["result"]) == len(svc.RULES)
    lex = call("lexicon")["result"]
    assert any(e["lemma"] == "كِتَاب" for e in lex)
    v = call("version")["result"]
    assert v["lexicon_entries"] == len(lex)


@pytest.mark.parametrize("params,needle", [
    ({}, "'word' is required"),
    ({"word": "ك" * 100}, "at most"),
    ({"word": 5}, "must be a string"),
    ({"word": "كتاب", "number": "trial"}, "invalid 'number'"),
    ({"word": "كتاب", "case": "vocative"}, "invalid 'case'"),
    ({"word": "كتاب", "construct": "yes"}, "boolean"),
    ({"word": "كتاب", "number": "dual", "kind": "broken"}, "only valid"),
])
def test_bad_params_are_rejected(params, needle):
    r = svc.handle(json.dumps({"id": 1, "op": "generate", "params": params}))
    assert not r["ok"] and needle in r["error"]


def test_internal_error_logs_the_traceback_but_replies_generically(monkeypatch, capsys):
    def broken(_params):
        raise KeyError("secret detail")
    monkeypatch.setitem(svc.OPS, "version", broken)
    r = call("version")
    assert r == {"id": 7, "ok": False, "error": "internal error: KeyError"}
    err = capsys.readouterr().err
    assert "Traceback" in err and "secret detail" in err and "'version'" in err


def test_malformed_requests():
    assert not svc.handle("not json")["ok"]
    assert not svc.handle("[1,2]")["ok"]
    assert "unknown op" in svc.handle('{"id":1,"op":"rm"}')["error"]
    assert not svc.handle('{"id":1,"op":"rules","params":[]}')["ok"]


def test_stdio_roundtrip_in_subprocess():
    lines = [json.dumps({"id": i, "op": "generate", "params": {"word": w, "number": "dual"}}, ensure_ascii=False)
             for i, w in enumerate(["كتاب", "عصا"])]
    out = subprocess.run([sys.executable, str(SERVICE)], input="\n".join(lines) + "\n",
                         capture_output=True, text=True, encoding="utf-8", timeout=30)
    replies = [json.loads(l) for l in out.stdout.splitlines()]
    assert [r["id"] for r in replies] == [0, 1]
    assert replies[1]["result"]["forms"][0]["text"] == "عصوان"
