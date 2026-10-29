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
    PERSIAN_TO_ARABIC,
    PERSIAN_YEH,
    TATWEEL,
    TEH_MARBUTA,
    VOCALIZATION_MARKS,
    YEH,
    is_combining_mark,
    is_quranic_mark,
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


_ALEF_MAP = str.maketrans({ALEF_HAMZA_ABOVE: ALEF, ALEF_HAMZA_BELOW: ALEF, ALEF_MADDA: ALEF, ALEF_WASLA: ALEF})
_STRIP_MARKS = str.maketrans(dict.fromkeys(VOCALIZATION_MARKS))


def strip_diacritics(text: str) -> str:
    """Remove vocalisation marks only. Hamza-bearing letters are kept intact."""
    return _nfc(text).translate(_STRIP_MARKS)


def _nfc(text: str) -> str:
    return text if unicodedata.is_normalized("NFC", text) else unicodedata.normalize("NFC", text)


def has_diacritics(text: str) -> bool:
    return any(ch in VOCALIZATION_MARKS for ch in unicodedata.normalize("NFC", text))


def normalize(text: str, options: NormalizationOptions = NormalizationOptions()) -> NormalizedText:
    out = unicodedata.normalize("NFC", text)
    if options.strip_tatweel:
        out = out.replace(TATWEEL, "")
    if options.strip_diacritics:
        out = strip_diacritics(out)
    if options.unify_alef:
        out = out.translate(_ALEF_MAP)
    if options.alef_maqsura_to_yeh:
        out = out.replace(ALEF_MAQSURA, YEH)
    if options.teh_marbuta_to_heh:
        out = out.replace(TEH_MARBUTA, HEH)
    return NormalizedText(original=text, normalized=out, options=options)


# Merges spellings that are grammatically distinct (أ/ا, ى/ي, ة/ه); used only to
# *suggest* a lexicon word ("did you mean"), never to replace the input.
LOSSY_OPTIONS = NormalizationOptions(
    strip_diacritics=True, unify_alef=True, alef_maqsura_to_yeh=True, teh_marbuta_to_heh=True,
)


# The lossy options as one table: every step maps single characters, so they combine.
_LOSSY_TABLE = {**_STRIP_MARKS, **_ALEF_MAP, ord(TATWEEL): None, ord(ALEF_MAQSURA): YEH, ord(TEH_MARBUTA): HEH}


def lossy_key(text: str) -> str:
    """normalize(text, LOSSY_OPTIONS).normalized, fast: it keys every lexicon entry."""
    return _nfc(text).translate(_LOSSY_TABLE)


@dataclass(frozen=True)
class FoldedInput:
    """User input with presentation forms, Persian letters and Quranic marks folded away."""
    original: str
    text: str
    warnings: tuple[str, ...]
    final_persian_yeh: bool     # the last letter was ی; it may stand for ي or ى


def fold_input(text: str) -> FoldedInput:
    """Fold spelling variants that never change the word: every change is reported as a warning."""
    warnings: list[str] = []
    out = unicodedata.normalize("NFKC", text)
    if out != unicodedata.normalize("NFC", text):
        warnings.append("Arabic presentation forms (or other compatibility characters) were folded "
                        "to standard letters.")

    quranic = [ch for ch in out if is_quranic_mark(ch)]
    if quranic:
        out = "".join(ch for ch in out if not is_quranic_mark(ch))
        warnings.append("Quranic annotation marks were removed: "
                        + " ".join(f"U+{ord(ch):04X}" for ch in dict.fromkeys(quranic)) + ".")

    letters = [ch for ch in out if not is_combining_mark(ch) and ch != TATWEEL]
    final_persian_yeh = bool(letters) and letters[-1] == PERSIAN_YEH
    for persian, arabic in PERSIAN_TO_ARABIC.items():
        if persian in out:
            out = out.replace(persian, arabic)
            warnings.append(f"The Persian letter {persian} (U+{ord(persian):04X}) was read as the Arabic {arabic}.")
    return FoldedInput(original=text, text=out, warnings=tuple(warnings), final_persian_yeh=final_persian_yeh)
