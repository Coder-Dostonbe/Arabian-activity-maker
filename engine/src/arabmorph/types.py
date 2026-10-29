"""Shared enums and result types for the morphology engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Case(StrEnum):
    NOMINATIVE = "nominative"   # رفع
    ACCUSATIVE = "accusative"   # نصب
    GENITIVE = "genitive"       # جر

    @property
    def arabic(self) -> str:
        return {"nominative": "رفع", "accusative": "نصب", "genitive": "جر"}[self.value]


class Number(StrEnum):
    SINGULAR = "singular"
    DUAL = "dual"
    PLURAL = "plural"


class PluralKind(StrEnum):
    SOUND_MASCULINE = "sound_masculine"   # جمع مذكر سالم
    SOUND_FEMININE = "sound_feminine"     # جمع مؤنث سالم
    BROKEN = "broken"                     # جمع تكسير


class Gender(StrEnum):
    MASCULINE = "masculine"
    FEMININE = "feminine"
    UNKNOWN = "unknown"


class FinalClass(StrEnum):
    """Classification of a noun by its final letter (relevant to dual/plural)."""
    SOUND = "sound"        # صحيح الآخر (includes ta marbuta and final hamza)
    MAQSUR = "maqsur"      # اسم مقصور: ends in a fixed alif (ى / ا)
    MANQUS = "manqus"      # اسم منقوص: ends in a fixed yeh preceded by kasra
    MAMDUD = "mamdud"      # اسم ممدود: ends in hamza after an extra alif


class AlifOrigin(StrEnum):
    """What the alif of a trilateral maqsur noun derives from."""
    WAW = "waw"
    YEH = "yeh"


class HamzaType(StrEnum):
    """The kind of hamza at the end of a mamdud noun."""
    ORIGINAL = "original"          # أصلية
    FEMININE = "feminine"          # للتأنيث
    SUBSTITUTED = "substituted"    # منقلبة عن واو أو ياء
    ILHAQ = "ilhaq"                # للإلحاق


class Source(StrEnum):
    RULE = "rule"              # deterministic rule from unambiguous evidence
    LEXICON = "lexicon"        # dictionary entry supplied the deciding fact
    HEURISTIC = "heuristic"    # inferred from spelling convention; may be wrong
    ASSERTED = "asserted"      # rule applied because the caller asserted it applies


class Status(StrEnum):
    OK = "ok"
    AMBIGUOUS = "ambiguous"
    ERROR = "error"


@dataclass(frozen=True)
class GeneratedForm:
    text: str                 # undiacritized
    vocalized: str            # suffix fully vocalised; stem as far as known
    number: Number
    case: Case
    definite: bool
    construct: bool
    rule_ids: tuple[str, ...]   # primary rule first
    source: Source
    confidence: float
    condition: str | None = None    # interpretation under which this form holds
    warnings: tuple[str, ...] = ()
    kind: PluralKind | None = None  # plural type, for plural forms only
    diptote: bool | None = None     # declined as ممنوع من الصرف

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "vocalized": self.vocalized,
            "number": self.number.value,
            "case": self.case.value,
            "definite": self.definite,
            "construct": self.construct,
            "rules": list(self.rule_ids),
            "source": self.source.value,
            "confidence": self.confidence,
            "condition": self.condition,
            "warnings": list(self.warnings),
            "kind": self.kind.value if self.kind else None,
            "diptote": self.diptote,
        }


@dataclass(frozen=True)
class GenerationResult:
    input: str
    status: Status
    forms: tuple[GeneratedForm, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = field(default=())
    suggestions: tuple[str, ...] = ()   # "did you mean": lexicon words close to the input; never applied

    def to_dict(self) -> dict:
        return {
            "input": self.input,
            "status": self.status.value,
            "forms": [f.to_dict() for f in self.forms],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "assumptions": list(self.assumptions),
            "suggestions": list(self.suggestions),
        }
