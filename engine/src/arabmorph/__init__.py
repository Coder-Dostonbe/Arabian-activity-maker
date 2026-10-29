"""ArabMorph engine: framework-independent Arabic morphology.

This package must not import Django, any web framework, or any AI provider.
"""

from .analyze import Analysis, AnalysisResult, analyze
from .context import case_from_context, generate_in_context
from .dual import dual_paradigm, generate_dual
from .generate import generate, paradigm
from .lexicon import Lexicon, LexiconEntry, PluralSpec
from .normalize import NormalizationOptions, NormalizedText, normalize, strip_diacritics
from .plural import generate_plural
from .rules import RULES, get_rule
from .singular import generate_singular
from .types import Case, FinalClass, GeneratedForm, GenerationResult, Number, PluralKind, Source, Status

__version__ = "0.2.0"

__all__ = [
    "Analysis", "AnalysisResult", "analyze",
    "Case", "case_from_context", "generate_in_context", "FinalClass", "GeneratedForm", "GenerationResult", "Lexicon", "LexiconEntry",
    "NormalizationOptions", "NormalizedText", "Number", "PluralKind", "PluralSpec", "RULES",
    "Source", "Status", "dual_paradigm", "generate", "generate_dual", "generate_plural",
    "generate_singular", "get_rule", "normalize", "paradigm", "strip_diacritics",
]
