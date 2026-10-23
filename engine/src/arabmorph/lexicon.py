"""In-memory lexicon of noun entries.

The engine consults the lexicon before falling back to rules, because some
facts (the origin of a maqsur alif, the type of a mamdud hamza, whether a
final yeh is manqus) cannot be recovered from spelling alone. In later phases
the same interface will be backed by the approved knowledge base.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

from .clusters import Cluster, split_clusters
from .normalize import strip_diacritics
from .types import AlifOrigin, FinalClass, Gender, HamzaType, PluralKind


@dataclass(frozen=True)
class PluralSpec:
    """A plural recorded for an entry.

    Broken plurals carry their vocalised form. Sound plurals usually carry no
    form: the entry only asserts that the noun takes that plural, and the rules
    build it.
    """
    kind: PluralKind
    form: str | None = None
    diptote: bool = False
    note: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> PluralSpec:
        kind = PluralKind(d["kind"])
        if kind is PluralKind.BROKEN and not d.get("form"):
            raise ValueError("a broken plural needs an explicit form")
        return cls(kind=kind, form=d.get("form"), diptote=bool(d.get("diptote", False)), note=d.get("note", ""))


@dataclass(frozen=True)
class LexiconEntry:
    id: str
    lemma: str                 # vocalised, without the definite article
    pos: str
    gender: Gender
    final_class: FinalClass
    alif_origin: AlifOrigin | None = None
    hamza_type: HamzaType | None = None
    gloss_en: str = ""
    diptote: bool = False          # the singular is ممنوع من الصرف
    plurals: tuple[PluralSpec, ...] = ()
    source: str = "seed"
    verified: bool = False

    @property
    def key(self) -> str:
        return strip_diacritics(self.lemma)

    @property
    def clusters(self) -> list[Cluster]:
        return split_clusters(self.lemma)

    @classmethod
    def from_dict(cls, d: dict, source: str) -> LexiconEntry:
        return cls(
            id=d["id"],
            lemma=d["lemma"],
            pos=d["pos"],
            gender=Gender(d.get("gender", "unknown")),
            final_class=FinalClass(d["final_class"]),
            alif_origin=AlifOrigin(d["alif_origin"]) if d.get("alif_origin") else None,
            hamza_type=HamzaType(d["hamza_type"]) if d.get("hamza_type") else None,
            gloss_en=d.get("gloss_en", ""),
            diptote=bool(d.get("diptote", False)),
            plurals=tuple(PluralSpec.from_dict(p) for p in d.get("plurals", ())),
            source=source,
            verified=bool(d.get("verified", False)),
        )


class Lexicon:
    def __init__(self, entries=()):
        self._by_key: dict[str, list[LexiconEntry]] = {}
        self._by_id: dict[str, LexiconEntry] = {}
        for e in entries:
            if e.id in self._by_id:
                raise ValueError(f"duplicate lexicon id {e.id}")
            self._by_key.setdefault(e.key, []).append(e)
            self._by_id[e.id] = e

    def lookup(self, bare_word: str) -> list[LexiconEntry]:
        return list(self._by_key.get(strip_diacritics(bare_word), ()))

    def get(self, entry_id: str) -> LexiconEntry | None:
        return self._by_id.get(entry_id)

    def __iter__(self):
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_key.values())

    @classmethod
    def empty(cls) -> Lexicon:
        return cls()

    @classmethod
    def from_json(cls, text: str) -> Lexicon:
        data = json.loads(text)
        source = f"{data.get('package', 'unknown')}@{data.get('version', '?')}"
        return cls(LexiconEntry.from_dict(d, source) for d in data["entries"])

    @classmethod
    def seed(cls) -> Lexicon:
        text = resources.files("arabmorph.data").joinpath("lexicon_seed.json").read_text(encoding="utf-8")
        return cls.from_json(text)
