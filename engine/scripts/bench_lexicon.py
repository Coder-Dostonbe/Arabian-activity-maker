"""Measure lexicon load time on synthetic files of a given size.

    python scripts/bench_lexicon.py 10000 20000 40000

Entries are copies of the seed with fresh ids, written to a temporary
lexicon_bench.json and loaded the way the engine loads its bundled files.
"""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from importlib import resources
from pathlib import Path

from arabmorph.lexicon import Lexicon


def bench(n: int, runs: int = 5) -> float:
    seed = json.loads(resources.files("arabmorph.data").joinpath("lexicon_seed.json").read_text(encoding="utf-8"))
    entries = [dict(seed["entries"][i % len(seed["entries"])], id=f"bench-{i}") for i in range(n)]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp, "lexicon_bench.json")
        path.write_text(json.dumps({"package": "bench", "version": "0", "entries": entries},
                                   ensure_ascii=False), encoding="utf-8")
        times = []
        for _ in range(runs):
            start = time.perf_counter()
            Lexicon.from_files([path])
            times.append(time.perf_counter() - start)
    return statistics.median(times)


def main(argv=None) -> int:
    sizes = [int(a) for a in (argv if argv is not None else sys.argv[1:])] or [10000, 20000, 40000]
    start = time.perf_counter()
    Lexicon.bundled()
    print(f"bundled files: {(time.perf_counter() - start) * 1000:.1f} ms")
    for n in sizes:
        print(f"{n:>7} entries: {bench(n) * 1000:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
