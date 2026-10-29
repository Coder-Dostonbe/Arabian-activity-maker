"""Convert an external lexicon source into the engine's lexicon JSON schema.

    python scripts/import_lexicon.py sample_lexicon.tsv --format tsv --source sample \
        --version 0.1 --license "CC0-1.0" -o ../src/arabmorph/data/lexicon_sample.json

Every imported entry is written with `verified: false` and a `source` tag; only
a specialist review may set `verified`. The output is validated before it is
written (unique ids, valid enums, vocalised broken plurals), and ids must not
collide with the lexicon files already next to the output.

Readers exist only for formats whose license has been confirmed. The `tsv`
format is the project's own hand-made layout, one entry per line:

    id  lemma  pos  gender  final_class  alif_origin  hamza_type  flags  plurals  gloss_en

`flags` is a comma list of `diptote`, `five_noun`. `plurals` is a `;` list of
`broken:<vocalised form>`, `sound_feminine`, `sound_feminine:<form>` or
`sound_masculine`; append `!diptote` to a broken form that is diptote.
Empty cells are written as `-`.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path

from arabmorph.lexicon import Lexicon, validate_document

TSV_COLUMNS = ("id", "lemma", "pos", "gender", "final_class", "alif_origin", "hamza_type",
               "flags", "plurals", "gloss_en")
FLAGS = {"diptote", "five_noun"}


class ImportProblem(ValueError):
    pass


def _cell(value: str) -> str | None:
    value = unicodedata.normalize("NFC", value.strip())
    return None if value in ("", "-") else value


def _plural(item: str) -> dict:
    kind, _, form = item.partition(":")
    out = {"kind": kind.strip()}
    form, diptote = (form[:-len("!diptote")], True) if form.endswith("!diptote") else (form, False)
    if form.strip():
        out["form"] = form.strip()
    if diptote:
        out["diptote"] = True
    return out


def read_tsv(path: Path):
    """Yield (line number, raw entry) from the hand-made TSV layout."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        for n, row in enumerate(csv.reader(f, delimiter="\t"), start=1):
            if not row or row[0].startswith("#") or row[0] == "id":
                continue
            if len(row) != len(TSV_COLUMNS):
                yield n, ImportProblem(f"expected {len(TSV_COLUMNS)} columns, found {len(row)}")
                continue
            cells = dict(zip(TSV_COLUMNS, map(_cell, row)))
            entry = {k: cells[k] for k in ("id", "lemma", "pos", "gender", "final_class",
                                           "alif_origin", "hamza_type", "gloss_en") if cells[k]}
            flags = {f.strip() for f in (cells["flags"] or "").split(",") if f.strip()}
            if flags - FLAGS:
                yield n, ImportProblem(f"unknown flags {sorted(flags - FLAGS)}")
                continue
            entry.update({flag: True for flag in sorted(flags)})
            plurals = [_plural(p) for p in (cells["plurals"] or "").split(";") if p.strip()]
            if plurals:
                entry["plurals"] = plurals
            yield n, entry


READERS = {"tsv": read_tsv}


def convert(rows, *, source: str, version: str, license: str, source_url: str = "",
            skip_invalid: bool = False, existing_ids=frozenset()) -> tuple[dict, list[str]]:
    """Build the lexicon document; returns it with the problems found (fatal unless skip_invalid)."""
    tag = f"{source}@{version}"
    entries, problems, seen = [], [], set(existing_ids)
    for n, raw in rows:
        if isinstance(raw, ImportProblem):
            problems.append(f"line {n}: {raw}")
            continue
        entry = dict(raw, id=f"{source}-{raw['id']}" if raw.get("id") else None, source=tag, verified=False)
        if entry["id"] in seen:
            entry_problems = [f"duplicate id {entry['id']}"
                              + (" (already in another lexicon file)" if entry["id"] in existing_ids else "")]
        else:
            entry_problems = validate_document({"package": source, "version": version, "entries": [entry]},
                                               allow_verified=False)
        if entry_problems:
            problems += [f"line {n}: {p}" for p in entry_problems]
            continue
        seen.add(entry["id"])
        entries.append(entry)
    doc = {
        "package": source,
        "version": version,
        "license": license,
        "source_url": source_url,
        "note": f"Imported from {source} {version}. Not reviewed by a language specialist: "
                "every entry is verified: false.",
        "entries": entries,
    }
    problems += validate_document(doc, allow_verified=False)
    if skip_invalid:
        return doc, problems
    return (doc if not problems else None), problems


def dumps(doc: dict) -> str:
    """One entry per line, in the layout of lexicon_seed.json, so diffs stay readable."""
    head = {k: v for k, v in doc.items() if k != "entries"}
    lines = [f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}," for k, v in head.items()]
    body = ",\n".join("    " + json.dumps(e, ensure_ascii=False) for e in doc["entries"])
    return "{\n" + "\n".join(lines) + '\n  "entries": [\n' + body + ("\n" if body else "") + "  ]\n}\n"


def _existing_ids(out: Path) -> set[str]:
    others = [f for f in out.parent.glob("lexicon_*.json") if f.resolve() != out.resolve()]
    return {e.id for e in Lexicon.from_files(others)} if others else set()


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="import_lexicon")
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=sorted(READERS), required=True)
    parser.add_argument("--source", required=True, help="short source name; becomes the id prefix and tag")
    parser.add_argument("--version", required=True, help="version of the source data")
    parser.add_argument("--license", required=True, help="license of the source data (must be confirmed)")
    parser.add_argument("--source-url", default="")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--skip-invalid", action="store_true", help="drop invalid entries instead of failing")
    args = parser.parse_args(argv)

    if not args.source.isascii() or not args.source.replace("_", "").isalnum():
        parser.error("--source must be ASCII letters, digits or _")
    if not args.output.name.startswith("lexicon_") or args.output.suffix != ".json":
        parser.error("the output file must be named lexicon_<source>.json")
    doc, problems = convert(READERS[args.format](args.input), source=args.source, version=args.version,
                            license=args.license, source_url=args.source_url,
                            skip_invalid=args.skip_invalid, existing_ids=_existing_ids(args.output))
    for p in problems:
        print(p, file=sys.stderr)
    if doc is None:
        print(f"{len(problems)} problem(s); nothing written.", file=sys.stderr)
        return 1
    args.output.write_text(dumps(doc), encoding="utf-8")
    print(f"{len(doc['entries'])} entries written to {args.output}"
          + (f"; {len(problems)} problem(s) skipped" if problems else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
