"""Command-line interface.

    python -m arabmorph dual كتاب --case accusative
    python -m arabmorph plural مهندس --construct
    python -m arabmorph singular أحمد --case genitive
    python -m arabmorph plural صحراء --all
    python -m arabmorph plural مدرسة --after في --definite     # case from the preceding word
    python -m arabmorph analyze كتب                            # which singular, number, case, state
"""

from __future__ import annotations

import argparse
import json
import sys

from .analyze import analyze
from .context import generate_in_context
from .generate import generate, paradigm
from .types import Case, Number, PluralKind


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="arabmorph")
    sub = parser.add_subparsers(dest="number", required=True)
    for number in Number:
        p = sub.add_parser(number.value, help=f"{number.value} forms of a singular noun")
        p.add_argument("word")
        p.add_argument("--case", choices=[c.value for c in Case], default=Case.NOMINATIVE.value)
        p.add_argument("--definite", action=argparse.BooleanOptionalAction, default=None)
        p.add_argument("--construct", action="store_true")
        p.add_argument("--all", action="store_true", help="full paradigm: 3 cases x 3 states")
        p.add_argument("--after", metavar="WORD", help="take the case from this preceding word (overrides --case)")
        if number is Number.PLURAL:
            p.add_argument("--kind", choices=[k.value for k in PluralKind], default=None,
                           help="only this plural type; for words without a lexicon entry this asserts it applies")
    p = sub.add_parser("analyze", help="candidate singulars of a dual, plural or declined form")
    p.add_argument("word")
    args = parser.parse_args(argv)

    if args.number == "analyze":
        out = analyze(args.word).to_dict()
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    number = Number(args.number)
    kind = PluralKind(args.kind) if getattr(args, "kind", None) else None
    if args.after:
        out = generate_in_context(args.word, number, args.after, definite=args.definite,
                                  construct=args.construct, kind=kind).to_dict()
    elif args.all:
        table = paradigm(args.word, number, kind=kind)
        out = {state: {c: r.to_dict() for c, r in row.items()} for state, row in table.items()}
    else:
        out = generate(args.word, number, Case(args.case), definite=args.definite,
                       construct=args.construct, kind=kind).to_dict()
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
