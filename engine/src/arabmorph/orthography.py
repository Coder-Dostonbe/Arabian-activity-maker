"""Orthographic helpers shared by the generators."""

from __future__ import annotations

from .chars import ALEF, ALEF_WASLA, KASRA, LAM, SHADDA, SUKUN, SUN_LETTERS
from .clusters import Cluster


def add_article(body: list[Cluster]) -> list[Cluster]:
    """Prefix ال: shadda on a following sun letter, sukun on lam before a moon letter.

    Before hamzat al-wasl (a bare initial alif) the lam takes kasra instead,
    so two quiescent letters do not meet (الِاجْتِمَاع).
    """
    first = body[0]
    if first.base in (ALEF, ALEF_WASLA):
        return [Cluster(ALEF), Cluster(LAM, KASRA)] + body
    if first.base in SUN_LETTERS:
        return [Cluster(ALEF), Cluster(LAM), first.with_marks(first.marks + SHADDA)] + body[1:]
    return [Cluster(ALEF), Cluster(LAM, SUKUN)] + body


def add_mark(cluster: Cluster, mark: str) -> Cluster:
    """Replace any case/vowel marks on `cluster` with `mark` (shadda is kept)."""
    c = cluster.without_case_marks()
    return c.with_marks(c.marks + mark)
