"""Arabic Unicode constants and character predicates.

Kept deliberately small and explicit: every linguistic module refers to these
names instead of raw code points, so the intent of each comparison is readable.
"""

# --- Diacritics (harakat, tanween, and related marks) ---------------------
FATHATAN = "ً"
DAMMATAN = "ٌ"
KASRATAN = "ٍ"
FATHA = "َ"
DAMMA = "ُ"
KASRA = "ِ"
SHADDA = "ّ"
SUKUN = "ْ"
MADDA_ABOVE = "ٓ"
HAMZA_ABOVE = "ٔ"
HAMZA_BELOW = "ٕ"
SUPERSCRIPT_ALEF = "ٰ"

TANWEEN = frozenset({FATHATAN, DAMMATAN, KASRATAN})
SHORT_VOWELS = frozenset({FATHA, DAMMA, KASRA})
# Marks that encode a case ending when they sit on the final letter.
CASE_MARKS = TANWEEN | SHORT_VOWELS | {SUKUN}
# Vocalisation marks: removing them loses pronunciation, not spelling.
VOCALIZATION_MARKS = CASE_MARKS | {SHADDA, SUPERSCRIPT_ALEF}
# Combining hamza/madda change the *letter* itself; they are not vocalisation.
COMBINING_MARKS = VOCALIZATION_MARKS | {MADDA_ABOVE, HAMZA_ABOVE, HAMZA_BELOW}

TATWEEL = "ـ"

# --- Letters ---------------------------------------------------------------
HAMZA = "ء"             # ء
ALEF_MADDA = "آ"        # آ
ALEF_HAMZA_ABOVE = "أ"  # أ
WAW_HAMZA = "ؤ"         # ؤ
ALEF_HAMZA_BELOW = "إ"  # إ
YEH_HAMZA = "ئ"         # ئ
ALEF = "ا"              # ا
TEH_MARBUTA = "ة"       # ة
TEH = "ت"               # ت
LAM = "ل"               # ل
NOON = "ن"              # ن
HEH = "ه"               # ه
WAW = "و"               # و
ALEF_MAQSURA = "ى"      # ى
YEH = "ي"               # ي
ALEF_WASLA = "ٱ"        # ٱ

# Persian-keyboard letters that users type in place of their Arabic counterparts.
PERSIAN_KAF = "ک"      # ک  U+06A9
PERSIAN_YEH = "ی"      # ی  U+06CC
KAF = "ك"              # ك
PERSIAN_TO_ARABIC = {PERSIAN_KAF: KAF, PERSIAN_YEH: YEH}


def is_quranic_mark(ch: str) -> bool:
    """Quranic annotation signs (small high letters, pause and recitation marks)."""
    return 0x0610 <= ord(ch) <= 0x061A or 0x06D6 <= ord(ch) <= 0x06ED

ALEF_VARIANTS = frozenset({ALEF, ALEF_MADDA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, ALEF_WASLA})
HAMZA_LETTERS = frozenset({HAMZA, ALEF_HAMZA_ABOVE, ALEF_HAMZA_BELOW, WAW_HAMZA, YEH_HAMZA, ALEF_MADDA})

# Letters that assimilate the lam of the definite article (الحروف الشمسية).
SUN_LETTERS = frozenset("تثدذرزسشصضطظلن")


def is_arabic_letter(ch: str) -> bool:
    """True for base Arabic letters (hamza through yeh, plus alef wasla)."""
    return "ء" <= ch <= "ي" or ch == ALEF_WASLA


def is_combining_mark(ch: str) -> bool:
    return ch in COMBINING_MARKS
