"""Configurable, non-destructive normalisation.

The original text is always returned alongside the normalised form. Options
that lose grammatical information (hamza seats, alef maqsura, ta marbuta) are
off by default and flag the result as lossy when enabled.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .chars import (
    ALEF,
    ALEF_HAMZA_ABOVE,
    ALEF_HAMZA_BELOW,
    ALEF_MADDA,
    ALEF_MAQSURA,
    ALEF_WASLA,
    HEH,
    TATWEEL,
    TEH_MARBUTA,
    VOCALIZATION_MARKS,
    YEH,
)


@dataclass(frozen=True)
class NormalizationOptions:
    strip_diacritics: bool = False
    strip_tatweel: bool = True
    unify_alef: bool = False            # أ إ آ ٱ → ا   (lossy: loses hamza)
    alef_maqsura_to_yeh: bool = False   # ى → ي        (lossy)
    teh_marbuta_to_heh: bool = False    # ة → ه        (lossy)

    @property
    def lossy(self) -> bool:
        return self.unify_alef or self.alef_maqsura_to_yeh or self.teh_marbuta_to_heh


# Preset for matching user input against stored entries: ignores vocalisation
# but keeps every spelling distinction that matters grammatically.
SEARCH_OPTIONS = NormalizationOptions(strip_diacritics=True)


@dataclass(frozen=True)
class NormalizedText:
    original: str
    normalized: str
    options: NormalizationOptions

    @property
    def lossy(self) -> bool:
        return self.options.lossy


_ALEF_MAP = {ALEF_HAMZA_ABOVE: ALEF, ALEF_HAMZA_BELOW: ALEF, ALEF_MADDA: ALEF, ALEF_WASLA: ALEF}


def strip_diacritics(text: str) -> str:
    """Remove vocalisation marks only. Hamza-bearing letters are kept intact."""
    text = unicodedata.normalize("NFC", text)
    return "".join(ch for ch in text if ch not in VOCALIZATION_MARKS)


def has_diacritics(text: str) -> bool:
    return any(ch in VOCALIZATION_MARKS for ch in unicodedata.normalize("NFC", text))


def normalize(text: str, options: NormalizationOptions = NormalizationOptions()) -> NormalizedText:
    out = unicodedata.normalize("NFC", text)
    if options.strip_tatweel:
        out = out.replace(TATWEEL, "")
    if options.strip_diacritics:
        out = strip_diacritics(out)
    if options.unify_alef:
        out = "".join(_ALEF_MAP.get(ch, ch) for ch in out)
    if options.alef_maqsura_to_yeh:
        out = out.replace(ALEF_MAQSURA, YEH)
    if options.teh_marbuta_to_heh:
        out = out.replace(TEH_MARBUTA, HEH)
    return NormalizedText(original=text, normalized=out, options=options)
