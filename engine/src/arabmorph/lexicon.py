"""In-memory lexicon of noun entries.

The engine consults the lexicon before falling back to rules, because some
facts (the origin of a maqsur alif, the type of a mamdud hamza, whether a
final yeh is manqus) cannot be recovered from spelling alone. In later phases
the same interface will be backed by the approved knowledge base.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from importlib import resources

from .chars import is_arabic_letter
from .clusters import Cluster, split_clusters
from .normalize import lossy_key, strip_diacritics
from .types import AlifOrigin, FinalClass, Gender, HamzaType, PluralKind


@dataclass(frozen=True)
class PluralSpec:
    """A plural recorded for an entry.

    Broken plurals carry their vocalised form. Sound plurals usually carry no
    form: the entry only asserts that the noun takes that plural, and the rules
    build it. A sound feminine plural may pin the attested `form` when the rules
    allow more than one spelling but usage settled on one (سماء ← سماوات).
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
        if kind is PluralKind.SOUND_MASCULINE and d.get("form"):
            raise ValueError("a sound masculine plural cannot pin a form")
        if kind is PluralKind.SOUND_FEMININE and d.get("form") and not strip_diacritics(d["form"]).endswith("ات"):
            raise ValueError("a pinned sound feminine plural must end in ـات")
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
    five_noun: bool = False        # one of الأسماء الخمسة (أب، أخ، حم): waw returns in the dual and construct
    plurals: tuple[PluralSpec, ...] = ()
    source: str = "seed"
    verified: bool = False

    @cached_property
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
            five_noun=bool(d.get("five_noun", False)),
            plurals=tuple(PluralSpec.from_dict(p) for p in d.get("plurals", ())),
            source=d.get("source") or source,
            verified=bool(d.get("verified", False)),
        )


class Lexicon:
    """Entries indexed by bare spelling, lossy spelling and recorded plural forms.

    Files are indexed from their raw JSON and each entry is built on first use,
    so loading a large lexicon costs only the indexing (see `from_files`).
    """

    def __init__(self, entries=()):
        self._by_key: dict[str, list[str]] = {}
        self._by_lossy: dict[str, list[str]] | None = None   # built on the first "did you mean" lookup
        self._by_plural: dict[str, list[str]] = {}
        self._entries: dict[str, LexiconEntry | None] = {}   # id → entry, None until built
        self._raw: dict[str, tuple[dict, str]] = {}           # id → (JSON object, file source tag)
        for e in entries:
            self._index(e.id, e.key, [p.form for p in e.plurals if p.form])
            self._entries[e.id] = e

    def _index(self, entry_id: str, key: str, plural_forms) -> None:
        if entry_id in self._entries:
            raise ValueError(f"duplicate lexicon id {entry_id}")
        self._entries[entry_id] = None
        self._by_key.setdefault(key, []).append(entry_id)
        self._by_lossy = None
        for form in plural_forms:
            self._by_plural.setdefault(strip_diacritics(form), []).append(entry_id)

    def _add_raw(self, data: dict) -> None:
        source = _source_tag(data)
        for d in data["entries"]:
            self._index(d["id"], strip_diacritics(d["lemma"]),
                        [p["form"] for p in d.get("plurals", ()) if p.get("form")])
            self._raw[d["id"]] = (d, source)

    def _resolve(self, ids) -> list[LexiconEntry]:
        return [self.get(i) for i in ids]

    def lookup(self, bare_word: str) -> list[LexiconEntry]:
        return self._resolve(self._by_key.get(strip_diacritics(bare_word), ()))

    def lookup_lossy(self, bare_word: str) -> list[LexiconEntry]:
        """Entries whose spelling differs from `bare_word` only in hamza seat, ى/ي or ة/ه."""
        if self._by_lossy is None:
            self._by_lossy = {}
            for key, ids in self._by_key.items():
                self._by_lossy.setdefault(lossy_key(key), []).extend(ids)
        return self._resolve(self._by_lossy.get(lossy_key(bare_word), ()))

    def singulars_of(self, bare_plural: str) -> list[LexiconEntry]:
        """Entries that record `bare_plural` as one of their plural forms."""
        return self._resolve(self._by_plural.get(strip_diacritics(bare_plural), ()))

    def get(self, entry_id: str) -> LexiconEntry | None:
        if entry_id not in self._entries:
            return None
        entry = self._entries[entry_id]
        if entry is None:
            d, source = self._raw.pop(entry_id)
            entry = self._entries[entry_id] = LexiconEntry.from_dict(d, source)
        return entry

    def __iter__(self):
        return iter(self._resolve(list(self._entries)))

    def __len__(self) -> int:
        return len(self._entries)

    @classmethod
    def empty(cls) -> Lexicon:
        return cls()

    @classmethod
    def from_json(cls, text: str) -> Lexicon:
        """One lexicon document, every entry built (and so checked) immediately."""
        data = json.loads(text)
        source = _source_tag(data)
        return cls(LexiconEntry.from_dict(d, source) for d in data["entries"])

    @classmethod
    def seed(cls) -> Lexicon:
        return cls.from_json(_data_file("lexicon_seed.json").read_text(encoding="utf-8"))

    @classmethod
    def bundled(cls, extra_files=()) -> Lexicon:
        """Every packaged lexicon_*.json, the hand-made seed first, then `extra_files` (e.g. a user lexicon);
        ids must be unique across all of them."""
        packaged = [f for f in resources.files("arabmorph.data").iterdir()
                    if f.name.startswith("lexicon_") and f.name.endswith(".json")]
        lexicon = cls.from_files(packaged)
        for f in extra_files:
            lexicon._add_raw(json.loads(f.read_text(encoding="utf-8")))
        return lexicon

    @classmethod
    def from_files(cls, files) -> Lexicon:
        """Several lexicon files, indexed now and built lazily; files are validated when imported."""
        lexicon = cls()
        for f in sorted(files, key=lambda f: (f.name != "lexicon_seed.json", f.name)):
            lexicon._add_raw(json.loads(f.read_text(encoding="utf-8")))
        return lexicon


def _data_file(name: str):
    return resources.files("arabmorph.data").joinpath(name)


def _source_tag(data: dict) -> str:
    return f"{data.get('package', 'unknown')}@{data.get('version', '?')}"


# --- schema validation -----------------------------------------------------------

POS = {"noun", "adjective", "proper_noun"}
_ENUM_FIELDS = {"gender": Gender, "final_class": FinalClass, "alif_origin": AlifOrigin, "hamza_type": HamzaType}
_ENTRY_FIELDS = {"id", "lemma", "pos", "gender", "final_class", "alif_origin", "hamza_type", "gloss_en",
                 "diptote", "five_noun", "plurals", "source", "verified"}
_PLURAL_FIELDS = {"kind", "form", "diptote", "note"}


def validate_document(data, *, allow_verified: bool = True) -> list[str]:
    """Problems that would make a lexicon file wrong or unloadable; an empty list means it is valid.

    Imported files are checked with `allow_verified=False`: only a specialist review may set `verified`.
    """
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return ["the document must be an object with an 'entries' list"]
    problems = [f"missing '{k}'" for k in ("package", "version") if not data.get(k)]
    seen: set[str] = set()
    for i, d in enumerate(data["entries"]):
        where = f"entry {i}" + (f" ({d.get('id')})" if isinstance(d, dict) and d.get("id") else "")
        if not isinstance(d, dict):
            problems.append(f"{where}: not an object")
            continue
        problems += [f"{where}: {p}" for p in _entry_problems(d, allow_verified)]
        if d.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(d.get("id"))
    return problems


def _entry_problems(d: dict, allow_verified: bool) -> list[str]:
    problems = [f"unknown field '{k}'" for k in d if k not in _ENTRY_FIELDS]
    for key in ("id", "lemma", "pos", "final_class"):
        if not isinstance(d.get(key), str) or not d[key]:
            problems.append(f"'{key}' is required")
    if problems:
        return problems
    if d["pos"] not in POS:
        problems.append(f"invalid pos {d['pos']!r}")
    for key, enum in _ENUM_FIELDS.items():
        if d.get(key) is not None and d[key] not in {m.value for m in enum}:
            problems.append(f"invalid {key} {d[key]!r}")
    if not _is_arabic_word(d["lemma"]):
        problems.append(f"lemma {d['lemma']!r} is not a single Arabic word")
    elif strip_diacritics(d["lemma"]) == d["lemma"]:
        problems.append("lemma is not vocalised")
    if d.get("verified") and not allow_verified:
        problems.append("imported entries must not be marked verified")
    if not isinstance(d.get("plurals", []), list):
        return problems + ["'plurals' must be a list"]
    for j, p in enumerate(d.get("plurals", [])):
        if not isinstance(p, dict):
            problems.append(f"plural {j}: not an object")
            continue
        problems += [f"plural {j}: unknown field '{k}'" for k in p if k not in _PLURAL_FIELDS]
        try:
            PluralSpec.from_dict(p)
        except (KeyError, ValueError) as exc:
            problems.append(f"plural {j}: {exc}")
            continue
        form = p.get("form")
        if form and not _is_arabic_word(form):
            problems.append(f"plural {j}: form {form!r} is not a single Arabic word")
        elif p["kind"] == PluralKind.BROKEN and strip_diacritics(form) == form:
            problems.append(f"plural {j}: broken plural {form!r} is not vocalised")
    if not problems:
        try:
            LexiconEntry.from_dict(d, "validate")
        except (KeyError, ValueError) as exc:
            problems.append(str(exc))
    return problems


def _is_arabic_word(text) -> bool:
    return isinstance(text, str) and bool(text) and all(is_arabic_letter(c) for c in strip_diacritics(text))
