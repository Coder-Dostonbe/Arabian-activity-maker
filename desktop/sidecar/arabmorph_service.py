"""Local engine service for the desktop app.

Speaks newline-delimited JSON over stdin/stdout - no network socket, so
nothing else on the machine can reach it. One request per line:

    {"id": 1, "op": "generate", "params": {...}}
    -> {"id": 1, "ok": true, "result": {...}}
    -> {"id": 1, "ok": false, "error": "..."}

Every parameter is validated here; the UI is not trusted to send valid input.
"""

from __future__ import annotations

import json
import sys

import arabmorph
from arabmorph import (
    RULES,
    Case,
    Number,
    PluralKind,
    generate,
    generate_in_context,
    paradigm,
)
from arabmorph.pipeline import default_lexicon

MAX_WORD = 64


class BadRequest(ValueError):
    pass


def _word(params: dict, key: str = "word", required: bool = True) -> str | None:
    value = params.get(key)
    if value is None or value == "":
        if required:
            raise BadRequest(f"'{key}' is required")
        return None
    if not isinstance(value, str) or len(value) > MAX_WORD:
        raise BadRequest(f"'{key}' must be a string of at most {MAX_WORD} characters")
    return value


def _enum(params: dict, key: str, enum, default=None):
    value = params.get(key, default)
    if value is None:
        return None
    try:
        return enum(value)
    except ValueError:
        raise BadRequest(f"invalid '{key}': {value!r}") from None


def _bool(params: dict, key: str, allow_none: bool = False):
    value = params.get(key, None if allow_none else False)
    if value is None and allow_none:
        return None
    if not isinstance(value, bool):
        raise BadRequest(f"'{key}' must be a boolean")
    return value


def _common(params: dict) -> dict:
    number = _enum(params, "number", Number, "dual")
    kind = _enum(params, "kind", PluralKind)
    if kind is not None and number is not Number.PLURAL:
        raise BadRequest("'kind' is only valid with number 'plural'")
    return dict(
        number=number,
        kind=kind,
        definite=_bool(params, "definite", allow_none=True),
        construct=_bool(params, "construct"),
    )


def op_version(_params: dict) -> dict:
    lexicon = default_lexicon()
    sources = sorted({e.source for e in lexicon})
    return {"engine": arabmorph.__version__, "rules": len(RULES), "lexicon_entries": len(lexicon),
            "lexicon_sources": sources}


def op_generate(params: dict) -> dict:
    word = _word(params)
    common = _common(params)
    after = _word(params, "after", required=False)
    if after:
        return generate_in_context(word, common.pop("number"), after, **common).to_dict()
    case = _enum(params, "case", Case, "nominative")
    return generate(word, common.pop("number"), case, **common).to_dict()


def op_paradigm(params: dict) -> dict:
    word = _word(params)
    number = _enum(params, "number", Number, "dual")
    kind = _enum(params, "kind", PluralKind)
    if kind is not None and number is not Number.PLURAL:
        raise BadRequest("'kind' is only valid with number 'plural'")
    table = paradigm(word, number, kind=kind)
    return {state: {c: r.to_dict() for c, r in row.items()} for state, row in table.items()}


def op_rules(_params: dict) -> list:
    return [r.to_dict() for r in RULES.values()]


def op_lexicon(_params: dict) -> list:
    out = []
    for e in default_lexicon():
        out.append({
            "id": e.id, "lemma": e.lemma, "pos": e.pos, "gender": e.gender.value,
            "final_class": e.final_class.value,
            "alif_origin": e.alif_origin.value if e.alif_origin else None,
            "hamza_type": e.hamza_type.value if e.hamza_type else None,
            "diptote": e.diptote, "gloss_en": e.gloss_en, "verified": e.verified, "source": e.source,
            "plurals": [{"kind": p.kind.value, "form": p.form, "diptote": p.diptote} for p in e.plurals],
        })
    return out


OPS = {
    "version": op_version,
    "generate": op_generate,
    "paradigm": op_paradigm,
    "rules": op_rules,
    "lexicon": op_lexicon,
}


def handle(line: str) -> dict:
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        return {"id": None, "ok": False, "error": "request is not valid JSON"}
    if not isinstance(request, dict):
        return {"id": None, "ok": False, "error": "request must be a JSON object"}
    rid = request.get("id")
    op = OPS.get(request.get("op"))
    params = request.get("params")
    params = {} if params is None else params
    if op is None:
        return {"id": rid, "ok": False, "error": f"unknown op {request.get('op')!r}"}
    if not isinstance(params, dict):
        return {"id": rid, "ok": False, "error": "'params' must be an object"}
    try:
        return {"id": rid, "ok": True, "result": op(params)}
    except BadRequest as exc:
        return {"id": rid, "ok": False, "error": str(exc)}
    except Exception as exc:  # never crash the service on one bad request
        return {"id": rid, "ok": False, "error": f"internal error: {type(exc).__name__}"}


def main() -> int:
    # utf-8-sig: some callers (e.g. Windows PowerShell pipes) prefix the stream with a BOM.
    stdin = open(sys.stdin.fileno(), encoding="utf-8-sig", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", closefd=False, newline="\n")
    default_lexicon()  # load once at startup, not on the first request
    for line in stdin:
        if not line.strip():
            continue
        stdout.write(json.dumps(handle(line), ensure_ascii=False) + "\n")
        stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
