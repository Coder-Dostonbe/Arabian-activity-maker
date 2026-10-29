"""Closed classes of function words, shared by input checks and context analysis.

All spellings are undiacritized. The lists are about governing effect on the
next noun, not a complete inventory of Arabic particles.
"""

from __future__ import annotations

PREPOSITIONS = {"في", "من", "إلى", "الى", "عن", "على"}
# Prepositions whose governing is real but conditional (they also have non-governing uses).
QUALIFIED_PREPOSITIONS = {
    "حتى": "حتى can also be a conjunction (عاطفة) or introduce a new sentence (ابتدائية); "
           "it governs the genitive only as a preposition.",
    "منذ": "With a noun of time منذ is usually a preposition, but the nominative (منذُ يومُ الجمعة) "
           "is also correct, read as a predicate.",
    "مذ": "With a noun of time مذ is usually a preposition, but the nominative is also correct, "
          "read as a predicate.",
    "رب": "رُبَّ governs only an indefinite noun, which is usually described (رُبَّ أخٍ لك).",
    "خلا": "As a preposition of exception خلا takes the genitive; read as a verb it takes the "
           "accusative, and after ما (ما خلا) only the accusative is allowed.",
    "عدا": "As a preposition of exception عدا takes the genitive; read as a verb it takes the "
           "accusative, and after ما (ما عدا) only the accusative is allowed.",
    "حاشا": "As a preposition of exception حاشا takes the genitive; read as a verb it takes the accusative.",
}
# Adverbs (ظروف) that are always annexed: the next noun is their muḍāf ilayh.
ADVERBS_MUDAF = {"عند", "بعد", "قبل", "مع", "بين", "فوق", "تحت", "أمام", "خلف", "حول", "دون"}

INNA_SISTERS = {"إن", "أن", "كأن", "لكن", "ليت", "لعل"}
SHADDA_REQUIRED = {"إن", "أن", "كأن", "لكن"}   # without shadda they are different particles
HAMZALESS_INNA = {"ان": ("إنّ", "أنّ")}   # ان without hamza: إنّ or أنّ was probably meant

# كان and its sisters with no attached subject pronoun: the next noun is their subject (nominative).
KANA_SISTERS = {
    "كان", "كانت", "أصبح", "أصبحت", "أمسى", "أمست", "أضحى", "أضحت",
    "ظل", "ظلت", "بات", "باتت", "صار", "صارت", "ليس", "ليست",
}
KANA_CONJUGATED = {
    "يكون", "تكون", "يصبح", "تصبح", "يمسي", "تمسي", "يضحي", "تضحي", "يظل", "تظل",
    "يبيت", "تبيت", "يصير", "تصير",
    "ما زال", "ما زالت", "ما دام", "ما دامت", "ما برح", "ما برحت", "ما فتئ", "ما فتئت",
    "ما انفك", "ما انفكت", "لا يزال", "لا تزال", "ما يزال", "ما تزال",
}
# Forms with an attached subject pronoun (ـوا، ـا، ـتا، ـتُ، ـنا…): the next noun is the predicate (accusative).
KANA_WITH_PRONOUN = {
    "كانوا", "كانا", "كانتا", "كنت", "كنا", "كن", "كنتم", "كنتما", "كنتن",
    "أصبحوا", "أصبحا", "أصبحتا", "أصبحنا", "أمسوا", "أضحوا", "ظلوا", "ظلا", "باتوا",
    "صاروا", "صارا", "ليسوا", "ليسا", "لستم", "لسنا", "لست",
    "يكونون", "تكونون", "يكونان", "تكونان", "نكون", "أكون",
    "ما زالوا", "ما زلنا", "ما زلت", "ما داموا", "لا يزالون", "لا تزالون", "ما يزالون",
}

LA_NAFIYA = {"لا"}

# Words that are never nouns; typing one as the noun to inflect is a mistake.
# (رب is left out: رَبّ "lord" is a noun.)
PARTICLES = (PREPOSITIONS | INNA_SISTERS | LA_NAFIYA
             | {"حتى", "منذ", "مذ", "خلا", "عدا", "حاشا", "لم", "لن", "قد", "هل"})
