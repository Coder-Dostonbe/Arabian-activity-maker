"""Local engine service for the desktop app.

Speaks newline-delimited JSON over stdin/stdout - no network socket, so
nothing else on the machine can reach it. One request per line:

    {"id": 1, "op": "generate", "params": {...}}
    -> {"id": 1, "ok": true, "result": {...}}
    -> {"id": 1, "ok": false, "error": "..."}

Every parameter is validated here; the UI is not trusted to send valid input.
"""

from __future__ import annotations

import base64
import binascii
import json
import sys
import traceback

import arabmorph
from arabmorph import (
    RULES,
    Case,
    Number,
    PluralKind,
    analyze,
    generate,
    generate_in_context,
    paradigm,
)
from arabmorph.pipeline import default_lexicon

import activity
import importers
import office_writer
import user_lexicon
import verify

MAX_WORD = 64
MAX_NAME = 260


class BadRequest(ValueError):
    def __init__(self, message: str, code: str = "bad_request"):
        super().__init__(message)
        self.code = code


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


def op_analyze(params: dict) -> dict:
    return analyze(_word(params)).to_dict()


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


def op_import_file(params: dict) -> dict:
    name = params.get("name")
    data = params.get("data")
    if not isinstance(name, str) or not name or len(name) > MAX_NAME:
        raise BadRequest(f"'name' must be a file name of at most {MAX_NAME} characters")
    if not isinstance(data, str) or len(data) > (importers.MAX_FILE_BYTES * 4) // 3 + 4:
        raise BadRequest("'data' must be base64 file content within the size limit", "too_large")
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise BadRequest("'data' is not valid base64") from None
    try:
        return importers.import_file(name, raw)
    except importers.FileImportError as exc:
        raise BadRequest(str(exc), exc.code) from None


def op_build_items(params: dict) -> dict:
    words = params.get("words")
    if not isinstance(words, list) or not words or len(words) > activity.MAX_WORDS:
        raise BadRequest(f"'words' must be a list of 1 to {activity.MAX_WORDS} words")
    for w in words:
        if not isinstance(w, str) or len(w) > MAX_WORD:
            raise BadRequest(f"every word must be a string of at most {MAX_WORD} characters")
    state = params.get("state", "indefinite")
    if state not in activity.STATES:
        raise BadRequest(f"invalid 'state': {state!r}")
    return activity.build_items(
        words,
        _enum(params, "number", Number, "dual"),
        _enum(params, "case", Case, "nominative"),
        state,
    )


def op_verify_items(params: dict) -> list:
    items = params.get("items")
    if not isinstance(items, list) or not items or len(items) > verify.MAX_ITEMS:
        raise BadRequest(f"'items' must be a list of 1 to {verify.MAX_ITEMS} items")
    for i in items:
        if not isinstance(i, dict) or not all(isinstance(i.get(k), str) and len(i[k]) <= verify.MAX_TEXT
                                              for k in ("prompt", "answer")):
            raise BadRequest(f"every item needs a 'prompt' and an 'answer' of at most {verify.MAX_TEXT} characters")
    return verify.verify_items(items)


def _entry(params: dict) -> dict:
    entry = params.get("entry")
    if not isinstance(entry, dict) or len(json.dumps(entry)) > 4000:
        raise BadRequest("'entry' must be a lexicon entry object")
    return entry


def op_user_lexicon(_params: dict) -> dict:
    try:
        return {"entries": user_lexicon.entries(), "configured": user_lexicon.path() is not None}
    except user_lexicon.UserLexiconError as exc:
        raise BadRequest(str(exc), "user_lexicon") from None


def op_user_lexicon_check(params: dict) -> dict:
    entry, problems = user_lexicon.check(_entry(params))
    return {"entry": entry, "problems": problems}


def op_user_lexicon_add(params: dict) -> dict:
    try:
        return user_lexicon.add(_entry(params))
    except user_lexicon.UserLexiconError as exc:
        raise BadRequest(str(exc), "user_lexicon") from None


def op_user_lexicon_remove(params: dict) -> dict:
    entry_id = params.get("id")
    if not isinstance(entry_id, str) or not entry_id.startswith("user-") or len(entry_id) > 40:
        raise BadRequest("'id' must be a user lexicon id")
    try:
        return {"removed": user_lexicon.remove(entry_id)}
    except user_lexicon.UserLexiconError as exc:
        raise BadRequest(str(exc), "user_lexicon") from None


MAX_SHEETS = 20
MAX_ROWS = 20000
SHEET_FORBIDDEN = set("[]:*?/" + chr(92))


def op_export_xlsx(params: dict) -> dict:
    """A workbook from {sheet name: rows of cells}, returned as base64 for the shell to save."""
    sheets = params.get("sheets")
    if not isinstance(sheets, dict) or not sheets or len(sheets) > MAX_SHEETS:
        raise BadRequest(f"'sheets' must map 1 to {MAX_SHEETS} sheet names to rows")
    clean = {}
    for name, rows in sheets.items():
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise BadRequest(f"each sheet must be a list of at most {MAX_ROWS} rows")
        # Excel sheet names: at most 31 characters, none of the characters Excel forbids in them.
        title = "".join(c for c in str(name) if c not in SHEET_FORBIDDEN)[:31] or "Sheet"
        clean[title] = [[str(c)[:1000] if c is not None else "" for c in row] if isinstance(row, list) else []
                        for row in rows]
    return {"data": base64.b64encode(office_writer.xlsx(clean)).decode("ascii")}


OPS = {
    "version": op_version,
    "generate": op_generate,
    "paradigm": op_paradigm,
    "analyze": op_analyze,
    "rules": op_rules,
    "lexicon": op_lexicon,
    "import_file": op_import_file,
    "build_items": op_build_items,
    "verify_items": op_verify_items,
    "user_lexicon": op_user_lexicon,
    "user_lexicon_check": op_user_lexicon_check,
    "user_lexicon_add": op_user_lexicon_add,
    "user_lexicon_remove": op_user_lexicon_remove,
    "export_xlsx": op_export_xlsx,
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
        return {"id": rid, "ok": False, "error": str(exc), "code": exc.code}
    except Exception as exc:  # never crash the service on one bad request
        # The full traceback goes to stderr, which the desktop shell writes to its log file;
        # the reply stays generic.
        print(f"internal error in op {request.get('op')!r} (id {rid!r}):", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return {"id": rid, "ok": False, "error": f"internal error: {type(exc).__name__}"}


def main() -> int:
    # utf-8-sig: some callers (e.g. Windows PowerShell pipes) prefix the stream with a BOM.
    stdin = open(sys.stdin.fileno(), encoding="utf-8-sig", closefd=False)
    stdout = open(sys.stdout.fileno(), "w", encoding="utf-8", closefd=False, newline="\n")
    for problem in user_lexicon.load():  # bundled + the teacher's own entries, once at startup
        print(problem, file=sys.stderr, flush=True)
    default_lexicon()
    for line in stdin:
        if not line.strip():
            continue
        stdout.write(json.dumps(handle(line), ensure_ascii=False) + "\n")
        stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
