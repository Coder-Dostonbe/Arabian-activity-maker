"""Letter clusters: a base letter plus the combining marks attached to it.

Morphological operations ("replace the final letter", "put a fatha on the last
letter") are expressed on clusters so diacritics travel with their letter and
are never dropped or misplaced by string slicing.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .chars import CASE_MARKS, TATWEEL, is_combining_mark


def canonical_marks(marks: str) -> str:
    """Order marks by Unicode combining class (the order NFC produces)."""
    return "".join(sorted(set(marks), key=unicodedata.combining))


@dataclass(frozen=True)
class Cluster:
    base: str
    marks: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "marks", canonical_marks(self.marks))

    def has(self, mark: str) -> bool:
        return mark in self.marks

    def with_marks(self, marks: str) -> Cluster:
        return Cluster(self.base, marks)

    def without(self, marks) -> Cluster:
        return Cluster(self.base, "".join(m for m in self.marks if m not in marks))

    def without_case_marks(self) -> Cluster:
        return self.without(CASE_MARKS)

    def render(self) -> str:
        return self.base + self.marks


def split_clusters(text: str) -> list[Cluster]:
    """Split text into clusters. Tatweel is cosmetic and is dropped.

    Raises ValueError if a combining mark has no base letter to attach to.
    """
    text = unicodedata.normalize("NFC", text)
    clusters: list[Cluster] = []
    for ch in text:
        if ch == TATWEEL:
            continue
        if is_combining_mark(ch):
            if not clusters:
                raise ValueError("text starts with a combining mark")
            last = clusters[-1]
            clusters[-1] = Cluster(last.base, last.marks + ch)
        else:
            clusters.append(Cluster(ch))
    return clusters


def join_clusters(clusters) -> str:
    return unicodedata.normalize("NFC", "".join(c.render() for c in clusters))


def bare(clusters) -> str:
    """Letters only, no marks."""
    return "".join(c.base for c in clusters)


def has_any_marks(clusters) -> bool:
    return any(c.marks for c in clusters)
