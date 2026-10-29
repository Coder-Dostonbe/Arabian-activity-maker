# arabmorph (engine)

Framework-independent Arabic morphology engine for ArabMorph AI. See the repository README for status and scope.

## Analysis

`analyze(word)` works backwards from a written form to its singular, number, case, state and plural
kind (`python -m arabmorph analyze كتب`). Candidates come from the lexicon's broken plurals and from
stripping sound suffixes; each one is kept only if generating it again gives the input exactly.

## Lexicon files

The engine loads every `src/arabmorph/data/lexicon_*.json` together, `lexicon_seed.json` first.
Entry ids must be unique across all the files.

`scripts/import_lexicon.py` converts an external source into this schema and validates it. Every
imported entry gets `verified: false` and a `source` tag; the output file is not written if any
check fails (or use `--skip-invalid`). For now the only reader is the project's own TSV layout
(see `scripts/sample_lexicon.tsv`). A reader for an external dictionary is added only once its
license has been confirmed.

`scripts/bench_lexicon.py` measures load time. Files are indexed when loaded and each entry is
built on first use. Measured on the development machine: 10k entries ≈ 80 ms, 20k ≈ 180 ms,
30k ≈ 230 ms, 40k ≈ 390 ms. The 300 ms budget therefore holds up to about 30k entries.
