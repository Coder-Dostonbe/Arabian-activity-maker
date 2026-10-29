"""The teacher's own lexicon entries, loaded in addition to the bundled lexicon.

Entries come from proposals the teacher approved (e.g. Claude's suggestion for
a word the engine could not handle). They are stored in `lexicon_user.json` in
the app data folder, whose path the desktop shell passes in
`ARABMORPH_USER_LEXICON`. Every entry is `verified: false`, `source: "user"`:
approval by the teacher is not a specialist review.
"""

from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path

from arabmorph import Lexicon, strip_diacritics
from arabmorph.lexicon import validate_document
from arabmorph.pipeline import default_lexicon, set_default_lexicon

ENV = "ARABMORPH_USER_LEXICON"
MAX_ENTRIES = 5000
FIELDS = ("lemma", "pos", "gender", "final_class", "alif_origin", "hamza_type", "gloss_en", "diptote", "plurals")


class UserLexiconError(ValueError):
    pass


def path() -> Path | None:
    value = os.environ.get(ENV)
    return Path(value) if value else None


def _read() -> dict:
    p = path()
    if p is None or not p.exists():
        return {"package": "user", "version": "1", "entries": []}
    doc = json.loads(p.read_text(encoding="utf-8"))
    if validate_document(doc, allow_verified=False):
        raise UserLexiconError("the user lexicon file is damaged")
    return doc


def _write(doc: dict) -> None:
    p = path()
    if p is None:
        raise UserLexiconError("no user lexicon file is configured")
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def load() -> list[str]:
    """Make the engine use the bundled lexicon plus the user file; returns problems (never raises)."""
    p = path()
    if p is None or not p.exists():
        set_default_lexicon(None)
        return []
    try:
        _read()
        set_default_lexicon(Lexicon.bundled([p]))
        return []
    except (UserLexiconError, ValueError, KeyError, OSError) as exc:
        set_default_lexicon(None)
        return [f"user lexicon not loaded: {exc}"]


def entries() -> list[dict]:
    return _read()["entries"]


def normalize_entry(raw: dict) -> dict:
    """A proposal reduced to the lexicon schema, with empty optional fields dropped."""
    if not isinstance(raw, dict):
        raise UserLexiconError("an entry must be an object")
    entry = {}
    for key in FIELDS:
        value = raw.get(key)
        if isinstance(value, str):
            value = unicodedata.normalize("NFC", value.strip())[:200]
        if value in (None, "", []):
            continue
        entry[key] = value
    plurals = []
    for p in entry.get("plurals", []) if isinstance(entry.get("plurals"), list) else []:
        if not isinstance(p, dict):
            continue
        plural = {"kind": p.get("kind")}
        if isinstance(p.get("form"), str) and p["form"].strip():
            plural["form"] = unicodedata.normalize("NFC", p["form"].strip())[:100]
        if p.get("diptote") is True:
            plural["diptote"] = True
        plurals.append(plural)
    if plurals:
        entry["plurals"] = plurals
    else:
        entry.pop("plurals", None)
    if entry.get("diptote") is not True:
        entry.pop("diptote", None)
    return entry


def check(raw: dict) -> tuple[dict, list[str]]:
    """The entry as it would be stored, and the schema problems that would stop it."""
    entry = dict(normalize_entry(raw), id="user-check", source="user", verified=False)
    problems = validate_document({"package": "user", "version": "1", "entries": [entry]}, allow_verified=False)
    return entry, [p.removeprefix("entry 0 (user-check): ") for p in problems]


def add(raw: dict) -> dict:
    doc = _read()
    if len(doc["entries"]) >= MAX_ENTRIES:
        raise UserLexiconError(f"the user lexicon is full ({MAX_ENTRIES} entries)")
    entry, problems = check(raw)
    if problems:
        raise UserLexiconError("; ".join(problems))
    used = {e["id"] for e in doc["entries"]}
    n = len(doc["entries"]) + 1
    while f"user-{n:04d}" in used:
        n += 1
    entry["id"] = f"user-{n:04d}"
    key = strip_diacritics(entry["lemma"])
    doc["entries"].append(entry)
    _write(doc)
    problems = load()
    if problems:
        raise UserLexiconError(problems[0])
    return {"entry": entry, "homographs": len(default_lexicon().lookup(key)) - 1}


def remove(entry_id: str) -> bool:
    doc = _read()
    kept = [e for e in doc["entries"] if e["id"] != entry_id]
    if len(kept) == len(doc["entries"]):
        return False
    doc["entries"] = kept
    _write(doc)
    load()
    return True
